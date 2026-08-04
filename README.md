# SmartDesk AI — Agentic RAG Support Assistant
🔗 **Live Demo:** https://smartdesk-ai-2emjgcwyos5bug3d7vgfkj.streamlit.app/
💻 **Backend API:** https://smartdesk-ai-backend-9h4d.onrender.com/docs
An AI support assistant for a CRM product ("CloudCRM") that can both **answer
questions** from product documentation (RAG) and **take actions** — looking up
live ticket status via a tool call — deciding which to do based on the query.
Remembers conversation context for natural follow-ups, degrades gracefully on
errors, and includes an automated evaluation harness. Runs entirely free.

## Features
- **Agentic routing** — decides per-query whether to retrieve from a knowledge
  base (RAG) or call a real backend tool (ticket lookup)
- **Conversation memory** — follow-up questions like *"any update on it?"*
  resolve correctly using recent chat history
- **Graceful error handling** — LLM/network failures return a helpful message
  instead of crashing; empty input is validated
- **Automated evaluation harness** (`eval.py`) — scores routing accuracy,
  answer relevance, and RAG faithfulness (LLM-as-judge) across a test suite
- **Dual deployment modes** — free local model (Ollama) for development, free
  cloud API (Groq) for the live deployed demo

## Architecture

```
User query + recent conversation history
    │
    ▼
[ROUTE]  LLM (+ deterministic fallback) decides: ticket lookup or FAQ question?
    │  also resolves follow-ups (e.g. "update on it?") using history
    │                              │
    ▼ (ticket)                     ▼ (FAQ)
[ACT]                        [ACT]
check_ticket_status()        retrieve_context() from ChromaDB
(mock CRM tool)              (vector search over product docs)
    │                              │
    └──────────► [RESPOND] ◄───────┘
           LLM generates final answer, grounded in
           tool result / retrieved chunks + history
                    │
                    ▼
              Answer shown in Streamlit UI
                    │
                    ▼
        [EVAL] eval.py scores routing accuracy,
        relevance, and faithfulness offline
```

## How to run (after completing SETUP_FIRST.md)

Open **3 terminals** in the `smartdesk-ai` folder.

**Terminal 1 — build the knowledge base (run once):**
```
python ingest.py
```
This reads `data/product_faq.md`, chunks it, embeds it, and stores it in a
local ChromaDB folder (`chroma_db/`).

**Terminal 2 — start the backend API:**
```
uvicorn api:app --reload --port 8000
```
Visit http://localhost:8000/docs to test it directly (Swagger UI).

**Terminal 3 — start the UI:**
```
streamlit run app.py
```
This opens a chat interface in your browser at http://localhost:8501

## Try asking:
- "What are the pricing plans?" → FAQ / RAG path
- "Does CloudCRM support SSO?" → FAQ / RAG path
- "What's the status of TCK-1004?" → Tool-call path (live ticket lookup)
- "Any update on ticket TCK-1002?" → Tool-call path

Watch the "action taken" label under each answer — it shows whether the
agent chose RAG retrieval or a tool call, which is the core thing to
point out in an interview demo.

## Running the evaluation harness
After the backend is set up (Ollama running, `ingest.py` already run once):
```
python eval.py
```
This runs a fixed test suite against the agent and prints a scorecard:
- **Routing accuracy** — did it correctly choose RAG vs tool-call?
- **Relevance** — does the answer contain the expected key facts?
- **Faithfulness** — for RAG answers, is the answer grounded in retrieved
  context (scored by an LLM-as-judge), not hallucinated?
- **Latency** — average response time per query

A detailed per-query breakdown is saved to `eval_report.json`. This is the
piece worth highlighting in interviews — it shows you're thinking about how
to *measure* an AI system's quality, not just build it.

## Project structure
```
smartdesk-ai/
├── data/
│   ├── product_faq.md      # mock company knowledge base (20 sections)
│   └── tickets.json        # mock CRM ticket database (10 tickets)
├── ingest.py                # builds the vector index (RAG setup)
├── tools.py                 # the "action" the agent can take
├── agent.py                 # core routing + RAG + tool-calling + memory logic
├── api.py                   # FastAPI backend (REST API)
├── app.py                   # Streamlit chat UI
├── eval.py                  # automated evaluation harness
├── render.yaml               # backend deployment config (Render)
├── DEPLOY.md                 # step-by-step deployment guide
├── requirements.txt
└── README.md
```

## What to say about this in an interview

- **"Why is this agentic, not just a chatbot?"** Because it doesn't only
  generate text — it decides whether to retrieve information or call a real
  backend function (ticket lookup), and acts on that decision. That
  route → act → respond loop is the same pattern used in production agent
  frameworks and tools like Salesforce Agentforce.
- **"How do you know the AI is actually giving good answers?"** The
  evaluation harness (`eval.py`) scores routing accuracy exactly, relevance
  via keyword coverage, and faithfulness via an LLM-as-judge that checks
  whether answers are actually grounded in retrieved context rather than
  hallucinated — the same category of technique used in real RAG evaluation
  tools like RAGAS.
- **"How does it handle multi-turn conversations?"** Recent conversation
  history is passed into both the routing decision and the answer generation
  step, so a follow-up like "any update on it?" after asking about a ticket
  correctly resolves which ticket "it" refers to.
- **"What happens if something fails — the LLM API, the vector DB?"**
  Failures are caught explicitly and produce a graceful fallback message
  (or, for ticket lookups, the raw data formatted directly) instead of
  crashing the request — a small thing, but it's the difference between a
  demo and something that behaves reasonably under real conditions.
- **"Why local model instead of an API?"** For local development, using
  Ollama keeps everything free. The live deployed version swaps to Groq's
  free API instead, since hosting platforms don't have enough RAM/CPU to
  run a local LLM — same code path, different backend, controlled by one
  environment variable.
- **"What would you improve with more time?"** Add a proper vector-store
  benchmark comparing retrieval strategies, stream responses token-by-token
  instead of waiting for the full answer, and expand the evaluation set
  significantly beyond 8 test cases.

## Next steps (optional further polish)
- Add a short demo video/GIF to this README
- Expand the evaluation test suite further
- Add authentication if this were to handle real customer data
