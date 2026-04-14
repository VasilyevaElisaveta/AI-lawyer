from typing import Any

from .base import BaseGraphAgent

from .....agents.simple_questions_agent import SimpleQuestionAgent


class SimpleAgent(BaseGraphAgent):
    def __init__(self):
        self.agent = SimpleQuestionAgent()

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        """
        Запускает агент простых вопросов.
        
        Returns:
            dict с полями:
            - reply: ответ на вопрос
            - handled_by_agent: флаг успешной обработки
            - document_created: был ли создан документ
        """
        result = await self.agent.process_user_message(message, thread_id)
        return {
            "reply": result.get("reply", ""),
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": False,
        }