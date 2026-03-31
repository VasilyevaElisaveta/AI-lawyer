from __future__ import annotations

from typing import Any

from ..contract_agent.llm_client import GigaChatClient
from .prompts import ANSWER_SYSTEM


class SimpleQuestionAgent:
    def __init__(self, llm: GigaChatClient | None = None) -> None:
        self.llm = llm or GigaChatClient()

    async def answer_question(self, question: str) -> str:
        return await self.llm.complete(system=ANSWER_SYSTEM, prompt=question)
