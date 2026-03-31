from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.contract_agent.agent import ContractAgent, AgentState

app = FastAPI(title="Contract Agent Web App", version="0.1.0")
agent = ContractAgent()


class ChatRequest(BaseModel):
    user_message: str
    state: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    reply: str
    state: dict[str, Any]
    exit_requested: bool = False
    missing_fields: list[str] = []
    qa_passed: bool = False
    generated_document: str = ""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    state = AgentState(request.state or {})
    response = await agent.process_user_message(request.user_message, state)
    return ChatResponse(
        reply=response.reply,
        state=response.state.to_dict(),
        exit_requested=response.exit_requested,
        missing_fields=response.missing_fields,
        qa_passed=response.qa_passed,
        generated_document=response.generated_document,
    )
