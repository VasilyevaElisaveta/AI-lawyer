from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.simple_questions_agent.agent import SimpleQuestionAgent

app = FastAPI(title="Simple Questions Agent Web App", version="0.1.0")
agent = SimpleQuestionAgent()


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    answer: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/answer", response_model=QuestionResponse)
async def answer_question(request: QuestionRequest) -> QuestionResponse:
    answer = await agent.answer_question(request.question)
    return QuestionResponse(answer=answer)
