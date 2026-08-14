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
GROQ_MODEL = "openai/gpt-oss-20b"  # fast, free-tier Groq model (migrated from
# llama-3.1-8b-instant, which Groq decommissioned Aug 16, 2026)

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "product_faq"
TOP_K = 3

# --- Vector DB (uses ChromaDB's built-in lightweight embedding function --
# no heavyweight ML libraries needed, keeps both local install and
# deployment fast and small) ---
_client = chromadb.PersistentClient(path=CHROMA_DIR)
_collection = _client.get_collection(COLLECTION_NAME)


class LLMUnavailableError(Exception):
    """Raised when the configured LLM backend can't be reached or errors out."""
    pass


def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """Send a prompt to whichever LLM backend is configured (Ollama or Groq).
    Raises LLMUnavailableError on any failure so callers can show a graceful
    message instead of crashing the request."""
    try:
        if LLM_PROVIDER == "groq":
            if not GROQ_API_KEY:
                raise LLMUnavailableError(
                    "LLM_PROVIDER is set to 'groq' but GROQ_API_KEY is not set."
                )
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

    except requests.exceptions.ConnectionError as e:
        if LLM_PROVIDER != "groq":
            raise LLMUnavailableError(
                "Can't reach Ollama. Make sure Ollama is running (open the Ollama "
                "app, or run 'ollama serve') and the model is pulled."
            ) from e
        raise LLMUnavailableError(f"Can't reach the Groq API: {e}") from e
    except requests.exceptions.Timeout as e:
        raise LLMUnavailableError("The LLM took too long to respond (timeout).") from e
    except requests.exceptions.HTTPError as e:
        raise LLMUnavailableError(f"LLM backend returned an error: {e}") from e
    except LLMUnavailableError:
        raise
    except Exception as e:
        raise LLMUnavailableError(f"Unexpected error calling the LLM: {e}") from e


def retrieve_context(query: str, k: int = TOP_K):
    """Fetch the top-k most relevant FAQ chunks from ChromaDB for the query.
    Returns an empty list (instead of crashing) if the vector DB has an issue,
    so the assistant can still respond with a fallback message."""
    try:
        results = _collection.query(query_texts=[query], n_results=k)
        return results.get("documents", [[]])[0]
    except Exception:
        return []


TICKET_ID_PATTERN = re.compile(r"TCK-\d{3,6}", re.IGNORECASE)
MAX_HISTORY_TURNS = 4  # how many past exchanges to feed back into prompts


def format_history(history: list) -> str:
    """Turn a list of {'role': 'user'|'assistant', 'content': str} into a
    short text block for prompt context. Keeps only the most recent turns
    so prompts stay small and fast, even in a long conversation."""
    if not history:
        return ""
    recent = history[-(MAX_HISTORY_TURNS * 2):]
    lines = [f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}" for h in recent]
    return "\n".join(lines)


def find_last_ticket_id(history: list) -> str | None:
    """Look back through recent conversation for the last ticket ID mentioned,
    so follow-up questions like 'any update on it?' can resolve what 'it' means."""
    if not history:
        return None
    for turn in reversed(history):
        match = TICKET_ID_PATTERN.search(turn.get("content", ""))
        if match:
            return match.group(0).upper()
    return None


def route_query(user_query: str, history: list = None) -> dict:
    """
    Decide whether this query needs the ticket-status tool or the FAQ knowledge base.
    Tries LLM-based routing first (more flexible), falls back to a deterministic
    keyword/regex check if the LLM output can't be parsed (more reliable).
    Also resolves follow-up references (e.g. "any update on it?") using
    conversation history.
    """
    history = history or []
    routing_prompt = f"""You are a routing classifier for a CRM support assistant.
Given the conversation so far and the user's latest message, decide which action to take.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"action": "ticket_status", "ticket_id": "TCK-XXXX"}}
or
{{"action": "faq"}}

Use "ticket_status" only if the user is asking about the status of a specific
support ticket AND a ticket ID (format TCK-XXXX) is known, either from the
current message or from the conversation history below. Otherwise use "faq".

Conversation so far:
{format_history(history) or "(none)"}

User's latest message: {user_query}
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
    is_status_question = any(w in user_query.lower() for w in ["status", "ticket", "update"])
    if id_match and is_status_question:
        return {"action": "ticket_status", "ticket_id": id_match.group(0).upper()}
    if not id_match and is_status_question:
        # follow-up like "any update on it?" -- try to resolve from history
        remembered_id = find_last_ticket_id(history)
        if remembered_id:
            return {"action": "ticket_status", "ticket_id": remembered_id}
    return {"action": "faq"}


def answer_ticket_status(user_query: str, ticket_id: str) -> dict:
    result = tools.check_ticket_status(ticket_id)

    if not result["found"]:
        answer = f"I couldn't find a ticket with ID {ticket_id}. Please double check the ticket number."
        return {
            "answer": answer,
            "action_taken": "tool_call: check_ticket_status",
            "sources": [],
            "raw_tool_result": result,
        }

    prompt = f"""You are a helpful CRM support assistant. A user asked about a support ticket.
Here is the live ticket data retrieved from the system:
{json.dumps(result, indent=2)}

Write a short, friendly, natural-language answer to the user's question using this data.
User's question: {user_query}
Answer:"""
    try:
        answer = call_llm(prompt, temperature=0.3)
    except LLMUnavailableError:
        # Graceful degradation: we still have the real ticket data, just
        # format it directly instead of failing the whole request.
        answer = (
            f"Ticket {result['ticket_id']}: \"{result['subject']}\" — status: "
            f"{result['status']}, priority: {result['priority']}, assigned to "
            f"{result['assigned_to']}, last updated {result['last_updated']}. "
            f"(Note: the AI assistant is temporarily unavailable, so this is the "
            f"raw ticket data.)"
        )

    return {
        "answer": answer,
        "action_taken": "tool_call: check_ticket_status",
        "sources": [],
        "raw_tool_result": result,
    }


def answer_faq(user_query: str, history: list = None) -> dict:
    history = history or []
    context_chunks = retrieve_context(user_query)

    if not context_chunks:
        return {
            "answer": "I couldn't search the knowledge base right now, so I'm not able to "
                      "answer that confidently. Please try again in a moment, or contact "
                      "support@cloudcrm.example.",
            "action_taken": "rag_retrieval (no context found)",
            "sources": [],
            "raw_tool_result": None,
        }

    context_text = "\n\n---\n\n".join(context_chunks)
    history_text = format_history(history)

    prompt = f"""You are a helpful CRM product support assistant for "CloudCRM".
Answer the user's question using ONLY the context below. If the answer isn't
in the context, say you don't have that information and suggest they contact
support@cloudcrm.example. Keep the answer concise (2-4 sentences).
Use the conversation history to understand follow-up questions (e.g. "what about X"),
but answer only the latest question.

Context:
{context_text}

Conversation so far:
{history_text or "(none)"}

User's latest question: {user_query}
Answer:"""

    try:
        answer = call_llm(prompt, temperature=0.2)
    except LLMUnavailableError as e:
        return {
            "answer": f"Sorry, I'm having trouble reaching the AI service right now ({e}). "
                      f"Please try again shortly.",
            "action_taken": "rag_retrieval (LLM error)",
            "sources": context_chunks,
            "raw_tool_result": None,
        }

    return {
        "answer": answer,
        "action_taken": "rag_retrieval",
        "sources": context_chunks,
        "raw_tool_result": None,
    }


def handle_query(user_query: str, history: list = None) -> dict:
    """Main entry point: route, act, respond. `history` is an optional list of
    {'role': 'user'|'assistant', 'content': str} dicts from earlier in the
    conversation, used to resolve follow-up questions."""
    history = history or []

    if not user_query or not user_query.strip():
        return {
            "answer": "Please type a question — I can help with CloudCRM product "
                      "questions or ticket status lookups.",
            "action_taken": "input_validation",
            "sources": [],
            "raw_tool_result": None,
        }

    try:
        route = route_query(user_query, history)
    except Exception:
        # If even routing fails unexpectedly, default to the safer FAQ path
        # rather than crashing the whole request.
        route = {"action": "faq"}

    if route["action"] == "ticket_status":
        return answer_ticket_status(user_query, route["ticket_id"])
    return answer_faq(user_query, history)


if __name__ == "__main__":
    # Quick manual test from the command line, now with conversation memory
    print("SmartDesk AI agent - type a question (or 'quit')\n")
    conversation = []
    while True:
        q = input("You: ").strip()
        if q.lower() in ("quit", "exit"):
            break
        result = handle_query(q, history=conversation)
        print(f"\n[action: {result['action_taken']}]")
        print(f"Assistant: {result['answer']}\n")
        conversation.append({"role": "user", "content": q})
        conversation.append({"role": "assistant", "content": result["answer"]})
