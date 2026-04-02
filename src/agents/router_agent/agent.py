from __future__ import annotations

from dataclasses import dataclass

from ..contract_agent.agent import ContractAgent
from ..simple_questions_agent.agent import SimpleQuestionAgent
from .config import Category, ROUTER_KEYWORDS


@dataclass
class RouterResponse:
    category: Category
    reply: str
    reason: str | None = None


class RouterAgent:
    def __init__(self) -> None:
        self.contract_agent = ContractAgent()
        self.simple_agent = SimpleQuestionAgent()

    async def route(self, user_message: str) -> RouterResponse:
        category = self._classify_message(user_message)

        if category == "simple_question":
            answer = await self.simple_agent.answer_question(user_message)
            return RouterResponse(
                category=category,
                reply=answer,
                reason="Общий вопрос обработан простым агентом.",
            )

        if category == "contract":
            contract_response = await self.contract_agent.process_user_message(user_message)
            return RouterResponse(
                category=category,
                reply=contract_response.reply,
                reason="Сообщение направлено в контрактного агента.",
            )

        if category == "pretrial_claim":
            return RouterResponse(
                category=category,
                reply="Ещё не реализовано. Обработчик претензий пока отсутствует.",
                reason="Сообщение классифицировано как претензия.",
            )

        return RouterResponse(
            category=category,
            reply="Ещё не реализовано. Обработчик иска пока отсутствует.",
            reason="Сообщение классифицировано как иск.",
        )

    def _classify_message(self, text: str) -> Category:
        normalized = text.lower()

        for category in ["pretrial_claim", "lawsuit", "contract"]:
            for pattern in ROUTER_KEYWORDS[category]:
                if pattern in normalized:
                    return category

        return "simple_question"
