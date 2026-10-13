import streamlit as st
import requests

st.set_page_config(page_title="SmartDesk AI", page_icon="🤖", layout="centered")

API_URL = "https://smartdesk-ai-backend-9h4d.onrender.com"

st.title("🤖 SmartDesk AI")
st.markdown("Agentic support assistant for CloudCRM — try asking a product question, or ask about a ticket like TCK-1001.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about a ticket or product question..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        with st.spinner("SmartDesk AI is thinking..."):
            res = requests.post(f"{API_URL}/chat", json={"query": prompt}, timeout=45)
        if res.status_code == 200:
            data = res.json()
            reply = data.get("response") or data.get("answer") or str(data)
        else:
            reply = f"Error {res.status_code}: {res.text}"
    except Exception as e:
        reply = f"Connection Error: {e}"
    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
