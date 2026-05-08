from typing import Any

from agents.claims_agent import ClaimsAgent

from .base import BaseGraphAgent


class ClaimsGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = ClaimsAgent(llm)

    async def run(
            self, 
            message: str, 
            thread_id: str, 
            user_metadata: dict[str, Any] = {}
        ) -> dict[str, Any]:
        result = await self.agent.process_user_message(message, thread_id, user_metadata=user_metadata)
        return {
            "reply": result.get("reply", ""),
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": result.get("document_created", False),
        }