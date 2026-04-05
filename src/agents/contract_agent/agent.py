from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph import ContractAgent as GraphAgent
from .llm_client import GigaChatClient
from .state import AgentState


@dataclass
class AgentResponse:
    reply: str
    state: AgentState
    exit_requested: bool = False
    missing_fields: list[str] = field(default_factory=list)
    qa_passed: bool = False
    generated_document: str = ""


class ContractAgent:
    def __init__(self, llm: GigaChatClient | None = None) -> None:
        self.graph_agent = GraphAgent(llm)

    async def process_user_message(self, user_message: str, state: AgentState | None = None) -> AgentResponse:
        if state is None:
            state = AgentState()

        # Запускаем граф
        result = await self.graph_agent.process_user_message(user_message, state)

        # Формируем ответ
        if result.get("error"):
            reply = result["error"]
            missing_fields = result.get("validation_errors", [])
            return AgentResponse(
                reply=reply,
                state=result,
                missing_fields=missing_fields,
            )
        elif result.get("final_document"):
            reply = result["final_document"]
            return AgentResponse(
                reply=reply,
                state=result,
                qa_passed=True,
                generated_document=reply,
            )
        else:
            # Другие случаи
            reply = "Обработка завершена, но результат не определён."
            return AgentResponse(reply=reply, state=result)
