"""
agent.py
The core "agentic" logic of SmartDesk AI.

Pipeline for every user query:
  1. ROUTE   -> ask the local LLM to decide: is this a ticket-status lookup,
                or a general product question? (Falls back to a keyword
                heuristic if the LLM's routing output can't be parsed --
                small local models occasionally produce malformed JSON,
                and a support tool needs to degrade gracefully, not crash.)
  2. ACT     -> if it's a ticket lookup, call the tools.check_ticket_status()
                function (a real backend action, not just text generation).
                Otherwise, retrieve relevant FAQ chunks from ChromaDB (RAG).
  3. RESPOND -> feed the tool result / retrieved context back into the LLM
                to produce a final natural-language answer.

This mirrors how real agent frameworks (LangChain agents, OpenAI function
calling, Salesforce Agentforce) work under the hood: route -> act -> respond.
"""

import os
import re
import json
import requests
import chromadb

import tools

# --- LLM provider config ---
# LLM_PROVIDER controls which "brain" answers questions:
#   "ollama" (default) -> free local model, used for laptop/dev demos
#   "groq"              -> free cloud API, used for the live deployed version
#                          (deployment platforms don't have enough RAM/CPU to run
#                          Ollama, so the live demo swaps to a free hosted model
#                          instead -- same code, same behavior, different backend)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # fast, free-tier Groq model

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "product_faq"
TOP_K = 3

# --- Vector DB (uses ChromaDB's built-in lightweight embedding function --
# no heavyweight ML libraries needed, keeps both local install and
# deployment fast and small) ---
_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _client.get_collection(COLLECTION_NAME)


def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """Send a prompt to whichever LLM backend is configured (Ollama or Groq)."""
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise RuntimeError("LLM_PROVIDER is set to 'groq' but GROQ_API_KEY is not set.")
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    # default: local Ollama
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def retrieve_context(query: str, k: int = TOP_K):
    """Fetch the top-k most relevant FAQ chunks from ChromaDB for the query."""
    results = _collection.query(query_texts=[query], n_results=k)
    docs = results.get("documents", [[]])[0]
    return docs


TICKET_ID_PATTERN = re.compile(r"TCK-\d{3,6}", re.IGNORECASE)


def route_query(user_query: str) -> dict:
    """
    Decide whether this query needs the ticket-status tool or the FAQ knowledge base.
    Tries LLM-based routing first (more flexible), falls back to a deterministic
    keyword/regex check if the LLM output can't be parsed (more reliable).
    """
    routing_prompt = f"""You are a routing classifier for a CRM support assistant.
Given the user's message, decide which action to take.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"action": "ticket_status", "ticket_id": "TCK-XXXX"}}
or
{{"action": "faq"}}

Use "ticket_status" only if the user is asking about the status of a specific
support ticket AND mentions a ticket ID (format TCK-XXXX). Otherwise use "faq".

User message: {user_query}
JSON response:"""

    try:
        raw = call_llm(routing_prompt, temperature=0.0)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if parsed.get("action") == "ticket_status" and parsed.get("ticket_id"):
                return {"action": "ticket_status", "ticket_id": parsed["ticket_id"]}
            if parsed.get("action") == "faq":
                return {"action": "faq"}
    except Exception:
        pass  # fall through to heuristic backup below

    # --- Deterministic fallback (keeps the demo reliable even if the LLM misfires) ---
    id_match = TICKET_ID_PATTERN.search(user_query)
    if id_match and any(w in user_query.lower() for w in ["status", "ticket", "update"]):
        return {"action": "ticket_status", "ticket_id": id_match.group(0).upper()}
    return {"action": "faq"}


def answer_ticket_status(user_query: str, ticket_id: str) -> dict:
    result = tools.check_ticket_status(ticket_id)

    if not result["found"]:
        answer = f"I couldn't find a ticket with ID {ticket_id}. Please double check the ticket number."
    else:
        prompt = f"""You are a helpful CRM support assistant. A user asked about a support ticket.
Here is the live ticket data retrieved from the system:
{json.dumps(result, indent=2)}

Write a short, friendly, natural-language answer to the user's question using this data.
User's question: {user_query}
Answer:"""
        answer = call_llm(prompt, temperature=0.3)

    return {
        "answer": answer,
        "action_taken": "tool_call: check_ticket_status",
        "sources": [],
        "raw_tool_result": result,
    }


def answer_faq(user_query: str) -> dict:
    context_chunks = retrieve_context(user_query)
    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "No relevant context found."

    prompt = f"""You are a helpful CRM product support assistant for "CloudCRM".
Answer the user's question using ONLY the context below. If the answer isn't
in the context, say you don't have that information and suggest they contact
support@cloudcrm.example. Keep the answer concise (2-4 sentences).

Context:
{context_text}

User's question: {user_query}
Answer:"""

    answer = call_llm(prompt, temperature=0.2)
    return {
        "answer": answer,
        "action_taken": "rag_retrieval",
        "sources": context_chunks,
        "raw_tool_result": None,
    }


def handle_query(user_query: str) -> dict:
    """Main entry point: route, act, respond."""
    route = route_query(user_query)
    if route["action"] == "ticket_status":
        return answer_ticket_status(user_query, route["ticket_id"])
    return answer_faq(user_query)


if __name__ == "__main__":
    # Quick manual test from the command line
    print("SmartDesk AI agent - type a question (or 'quit')\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in ("quit", "exit"):
            break
        result = handle_query(q)
        print(f"\n[action: {result['action_taken']}]")
        print(f"Assistant: {result['answer']}\n")
