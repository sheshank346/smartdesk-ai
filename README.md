# SmartDesk AI — Agentic RAG Support Assistant

An AI-powered support assistant for a CRM product ("CloudCRM") built with an **Agentic RAG architecture**. SmartDesk AI can both **answer product questions** using retrieval-augmented generation (RAG) and **take actions**—such as fetching live ticket status via dynamic tool calls—by intelligently routing queries based on user intent.

> 🚀 **Live Interactive App:** [https://smartdesk-ai-2emjgcwyos5bug3d7vgfkj.streamlit.app](https://smartdesk-ai-2emjgcwyos5bug3d7vgfkj.streamlit.app)  
> 🔗 **Live Backend API Docs:** [https://YOUR-RENDER-API-URL.onrender.com/docs](https://YOUR-RENDER-API-URL.onrender.com/docs)

---

## 📊 Evaluation & Benchmark Performance

SmartDesk AI is validated using an automated testing harness (`run_eval.py`) across core capabilities: intent routing, RAG retrieval quality, and tool execution accuracy.

![SmartDesk AI Evaluation Report](assets/evaluation_score.png)
=====
📊 SMARTDESK AI - EVALUATION REPORT (50 Test Cases)
Total Test Cases : 50
Passed           : 47
Failed           : 3
🎯 Success Rate  : 94.00%
<img width="512" height="288" alt="image" src="https://github.com/user-attachments/assets/cb11d880-7568-4abd-9460-47e07401d15c" />
## 🏗 Architecture & Agentic Flow
User Query
│
▼
[ROUTE]  LLM decides: ticket lookup or FAQ question?
│                               │
▼ (ticket)                      ▼ (FAQ)
[ACT]                           [ACT]
check_ticket_status()           retrieve_context() from ChromaDB
(mock CRM tool)                 (vector search over product docs)
│                               │
└──────────► [RESPOND] ◄────────┘
LLM generates final answer
grounded in tool result / retrieved chunks
│
▼
Answer shown in Streamlit UI
---

## 🚀 Key Features

* **Intent Routing Engine:** Dynamically routes user requests to either vector search (RAG) or executable local tools based on semantic intent.
* **Deterministic Fallback Layer:** Built-in keyword and pattern matching to prevent LLM parsing failures from breaking the workflow.
* **RAG Vector Search:** Powered by `ChromaDB` and local embeddings to query domain documentation accurately.
* **FastAPI Backend & Streamlit UI:** Fully decoupled architecture allowing REST API access alongside an intuitive web interface.
* **Live Deployment:** Streamlit web UI hosted on Streamlit Cloud with the FastAPI backend deployed on Render.

---

## 📁 Project Structure

```text
smartdesk-ai/
├── assets/
│   └── evaluation_score.png   # Evaluation benchmark screenshot
├── data/
│   ├── product_faq.md         # Knowledge base document
│   └── tickets.json           # Mock CRM database for tool actions
├── chroma_db/                 # Local vector database (generated)
├── ingest.py                  # Chunking and embedding ingestion pipeline
├── tools.py                   # Tool definitions (e.g., ticket lookup)
├── agent.py                   # Core routing, RAG, and execution logic
├── api.py                     # FastAPI REST server
├── app.py                     # Streamlit frontend user interface
├── run_eval.py                # Automated evaluation suite (50 test cases)
├── eval_dataset.json          # Benchmark dataset for evaluation
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation
⚙️ How to Run Locally
1. Build the Vector Knowledge Base (Run Once)
python ingest.py
Reads data/product_faq.md, generates vector embeddings, and populates the local ChromaDB store.

2. Start the FastAPI Backend
Bash
uvicorn api:app --reload --port 8000
Access interactive Swagger UI documentation locally at http://localhost:8000/docs.

3. Start the Streamlit User Interface
Bash
streamlit run app.py
Opens the web interface in your browser at http://localhost:8501.

4. Run the Automated Evaluation Harness
Bash
python run_eval.py
Executes the 50 test cases across tool calls, context retrieval, and edge cases to print accuracy metrics.

💡 Example Queries to Test
FAQ / RAG Path: "What are the pricing plans?"

FAQ / RAG Path: "Does CloudCRM support SSO?"

Tool-Call Path: "What's the status of TCK-1004?"

Tool-Call Path: "Any update on ticket TCK-1002?"

🎯 Technical & Portfolio Highlights
Agentic Execution Loop: Unlike basic prompt-response chatbots, SmartDesk AI implements a full Route → Act → Respond loop capable of triggering programmatic tool functions.

Resilience & Fallbacks: Employs a deterministic fallback layer so probabilistic LLM outputs never become a single point of failure.

Measured Reliability: Backed by an explicit 94.00% benchmark score on a 50-item evaluation harness, proving system robustness rather than relying on subjective manual testing.
