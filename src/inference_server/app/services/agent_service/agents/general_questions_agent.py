from typing import Any

from agents.general_questions_agent import GeneralQuestionsAgent

from .base import BaseGraphAgent


class GeneralQuestionsGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = GeneralQuestionsAgent(llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        """
        Запускает агент общих вопросов.
        
        Returns:
            dict с полями:
            - reply: ответ на вопрос
            - handled_by_agent: флаг успешной обработки
            - document_created: был ли создан документ
        """
        result = await self.agent.process_user_message(message, thread_id)
        error = result.get("error", None)
        reply = result.get("reply", "Ответ пустой")
        return {
            "reply": reply,
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": False,
            "error": error,
        }