from typing import Any

from agents.general_questions_agent import GeneralQuestionsAgent

from .base import BaseGraphAgent


class GeneralQuestionsGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = GeneralQuestionsAgent(llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        result = await self.agent.process_user_message(message, thread_id)
        response = result.get("response", {})
        metadata = result.get("metadata", {})
        metadata["process_name"] = "general_questions_agent"
        error = response.get("error", None)
        reply = response.get("reply", "Ответ пустой")
        return {
            "reply": reply,
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": False,
            "error": error,
            "metadata": metadata,
        }
