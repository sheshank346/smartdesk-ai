"""
app.py
Streamlit chat UI for SmartDesk AI. Talks to the FastAPI backend over HTTP,
just like a real frontend would talk to a production backend.

Run with (after starting api.py in another terminal):
    streamlit run app.py
"""

import requests
import streamlit as st

API_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="SmartDesk AI", page_icon="🤖", layout="centered")
st.title("🤖 SmartDesk AI")
st.caption("Agentic support assistant for CloudCRM — try asking a product question, "
           "or ask about a ticket like **TCK-1001**.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("action"):
            st.caption(f"⚙️ action taken: `{msg['action']}`")

# Chat input
user_input = st.chat_input("Ask a question about CloudCRM, or about a ticket (e.g. TCK-1001)...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(API_URL, json={"query": user_input}, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                answer = data["answer"]
                action = data["action_taken"]
                sources = data.get("sources", [])
            except Exception as e:
                answer = f"Error reaching backend: {e}. Is `uvicorn api:app` running on port 8000?"
                action = None
                sources = []

            st.markdown(answer)
            if action:
                st.caption(f"⚙️ action taken: `{action}`")
            if sources:
                with st.expander("📄 Retrieved FAQ context (RAG sources)"):
                    for i, s in enumerate(sources, 1):
                        st.markdown(f"**Chunk {i}:**\n\n{s}")

    st.session_state.messages.append({"role": "assistant", "content": answer, "action": action})

with st.sidebar:
    st.header("About this demo")
    st.markdown(
        "This assistant demonstrates an **agentic RAG pipeline**:\n\n"
        "1. **Route** — an LLM decides if this needs a live tool call "
        "(ticket lookup) or a knowledge-base answer (RAG)\n"
        "2. **Act** — calls a mock CRM ticket API, or retrieves relevant "
        "FAQ chunks from ChromaDB\n"
        "3. **Respond** — the LLM generates a final answer grounded in "
        "the tool result or retrieved context\n\n"
        "Try: *\"What's the status of TCK-1004?\"* vs "
        "*\"What are the pricing plans?\"*"
    )
    st.divider()
    st.caption("Running 100% locally via Ollama — no API costs.")
