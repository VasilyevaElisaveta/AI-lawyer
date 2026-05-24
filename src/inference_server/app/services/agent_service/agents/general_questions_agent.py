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
            - task_completed: задача успешно завершена
        """
        result = await self.agent.process_user_message(message, thread_id)
        response = result.get("response", {})
        metadata = result.get("metadata", {})
        metadata["process_name"] = "general_questions_agent"
        error = response.get("error", None)
        reply = response.get("reply", "Ответ пустой")
        task_completed = bool(reply) and not error
        return {
            "reply": reply,
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": False,
            "error": error,
            "metadata": metadata,
            "task_completed": task_completed,
        }
