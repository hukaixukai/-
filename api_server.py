# new-agent/api_server.py
"""FastAPI server entry point — serves REST API for the study companion."""

import uvicorn
from fastapi import FastAPI

from config import API_HOST, API_PORT, LLM_API_BASE, LLM_API_KEY, LLM_MODEL, EMBEDDING_API_BASE, EMBEDDING_API_KEY, EMBEDDING_MODEL
from llm.client import ChatClient, EmbeddingClient
from chat.session import SessionManager
from api import routes

app = FastAPI(
    title="智能学伴 API",
    description="AI-powered intelligent study companion — REST API",
    version="0.1.0",
)

# Initialize clients
chat_client = ChatClient(LLM_API_BASE, LLM_API_KEY, LLM_MODEL)
embed_client = EmbeddingClient(EMBEDDING_API_BASE, EMBEDDING_API_KEY, EMBEDDING_MODEL)
session_mgr = SessionManager(chat_client)

# Initialize API routes
routes.init(chat_client, embed_client, session_mgr)
app.include_router(routes.router)


@app.get("/")
async def root():
    return {"name": "智能学伴 API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    print(f"Starting 智能学伴 API server at http://{API_HOST}:{API_PORT}")
    print(f"API docs: http://{API_HOST}:{API_PORT}/docs")
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
