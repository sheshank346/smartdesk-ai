"""
api.py
FastAPI backend that exposes the SmartDesk AI agent as a REST API.

Run with:
    uvicorn api:app --reload --port 8000

Then test with:
    curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"query\": \"What is the pricing?\"}"

Or just open http://localhost:8000/docs for the interactive Swagger UI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import agent

app = FastAPI(
    title="SmartDesk AI",
    description="Agentic RAG-based support assistant for CloudCRM",
    version="1.0.0",
)

# Allow the deployed Streamlit frontend (a different domain) to call this API.
# For a portfolio/demo project this is fine; a real production app would
# restrict allow_origins to the specific frontend domain instead of "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    action_taken: str
    sources: list[str]


@app.get("/")
def root():
    return {"status": "SmartDesk AI is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = agent.handle_query(request.query)
    return ChatResponse(
        answer=result["answer"],
        action_taken=result["action_taken"],
        sources=result["sources"],
    )
