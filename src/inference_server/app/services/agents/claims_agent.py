from typing import Any

from .base import BaseGraphAgent

from .....agents.claims_agent import ClaimsAgent


class ClaimsGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = ClaimsAgent(llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        result = await self.agent.process_user_message(message, thread_id)
        return {
            "reply": result.get("reply", ""),
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": False,
        }