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
from pydantic import BaseModel

import agent

app = FastAPI(
    title="SmartDesk AI",
    description="Agentic RAG-based support assistant for CloudCRM",
    version="1.0.0",
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
