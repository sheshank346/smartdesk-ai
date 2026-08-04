# SmartDesk AI — Agentic RAG Support Assistant
🔗 **Live Demo:** https://smartdesk-ai-2emjgcwyos5bug3d7vgfkj.streamlit.app/
💻 **Backend API:** https://smartdesk-ai-backend-9h4d.onrender.com/docs
An AI support assistant for a CRM product ("CloudCRM") that can both **answer
questions** from product documentation (RAG) and **take actions** — looking up
live ticket status via a tool call — deciding which to do based on the query.
Runs entirely free, locally, using Ollama.

## Architecture

```
User query
    │
    ▼
[ROUTE]  LLM decides: ticket lookup or FAQ question?
    │                              │
    ▼ (ticket)                     ▼ (FAQ)
[ACT]                        [ACT]
check_ticket_status()        retrieve_context() from ChromaDB
(mock CRM tool)              (vector search over product docs)
    │                              │
    └──────────► [RESPOND] ◄───────┘
           LLM generates final answer
           grounded in tool result / retrieved chunks
                    │
                    ▼
              Answer shown in Streamlit UI
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

## Project structure
```
smartdesk-ai/
├── data/
│   ├── product_faq.md      # mock company knowledge base
│   └── tickets.json        # mock CRM ticket database (simulates a real API)
├── ingest.py                # builds the vector index (RAG setup)
├── tools.py                 # the "action" the agent can take
├── agent.py                 # core routing + RAG + tool-calling logic
├── api.py                   # FastAPI backend (REST API)
├── app.py                   # Streamlit chat UI
├── requirements.txt
└── README.md
```

## What to say about this in an interview

- **"Why is this agentic, not just a chatbot?"** Because it doesn't only
  generate text — it decides whether to retrieve information or call a real
  backend function (ticket lookup), and acts on that decision. That
  route → act → respond loop is the same pattern used in production agent
  frameworks and tools like Salesforce Agentforce.
- **"Why local model instead of an API?"** To keep it fully free while
  building, and to demonstrate understanding of self-hosted vs. API-based
  trade-offs (latency, cost, data privacy, model quality) — a real
  engineering decision, not just a limitation.
- **"How do you handle unreliable routing from a small model?"** There's a
  deterministic keyword/regex fallback if the LLM's JSON routing output
  can't be parsed — this is a resilience pattern: never let a probabilistic
  component be a single point of failure in a system a user depends on.
- **"What would you improve with more time?"** Add the evaluation harness
  (faithfulness/relevance scoring), swap the mock ticket JSON for a real
  database, add conversation memory across turns, and add streaming
  responses instead of waiting for the full answer.

## Next steps (after today, not required for the first working version)
- Add an evaluation script scoring answer faithfulness/relevance
- Deploy the API + UI on a free host (Render/Railway/HF Spaces) for a live demo link
- Push to GitHub with this README as-is — it doubles as your project write-up
