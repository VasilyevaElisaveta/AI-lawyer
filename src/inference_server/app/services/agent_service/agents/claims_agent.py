from typing import Any

from agents.claims_agent import ClaimsAgent

from .base import BaseGraphAgent


class ClaimsGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = ClaimsAgent(llm)

    async def get_current_agent(self, thread_id: str) -> str | None:
        return await self.agent.get_current_agent(thread_id)

    async def check_continue_task(self, message: str, thread_id: str) -> bool:
        return await self.agent.check_continue_task(message, thread_id)

    async def clear_session(self, thread_id: str) -> None:
        await self.agent.clear_session(thread_id)

    async def run(
            self,
            message: str,
            thread_id: str,
            user_metadata: dict[str, Any] | None = None,
            document_type: str | None = None,
        ) -> dict[str, Any]:
        user_metadata = user_metadata or {}
        result = await self.agent.process_user_message(
            message,
            thread_id,
            user_metadata=user_metadata,
            document_type=document_type or "lawsuit",
        )
        metadata = result.get("metadata", {}) or {}
        metadata["process_name"] = "claims_agent"
        return {
            "reply": result.get("reply", ""),
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": result.get("document_created", False),
            "awaiting_input": result.get("awaiting_input", False),
            "current_agent": result.get("current_agent"),
            "task_completed": result.get("task_completed", False),
            "metadata": metadata,
            "error": result.get("error"),
        }
