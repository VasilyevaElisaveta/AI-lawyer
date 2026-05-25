from typing import Any, AsyncIterator

from agents.general_questions_agent import GeneralQuestionsAgent

from .base import BaseGraphAgent


def _shape_general_result(raw: dict[str, Any]) -> dict[str, Any]:
    response = raw.get("response", {}) or {}
    metadata = raw.get("metadata", {}) or {}
    metadata["process_name"] = "general_questions_agent"
    return {
        "reply": response.get("reply", "Ответ пустой"),
        "handled_by_agent": True,
        "document_created": False,
        "error": response.get("error"),
        "metadata": metadata,
    }


class GeneralQuestionsGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = GeneralQuestionsAgent(llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        raw = await self.agent.process_user_message(message, thread_id)
        return _shape_general_result(raw)

    async def astream(
        self,
        message: str,
        thread_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Стримит чанки ответа (channel='progress') и финальный result."""
        async for event in self.agent.astream_user_message(message, thread_id):
            if event.get("channel") == "result":
                yield {"channel": "result", "data": _shape_general_result(event["data"])}
            else:
                yield event
