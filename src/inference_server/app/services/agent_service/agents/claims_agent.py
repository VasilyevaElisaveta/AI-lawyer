from typing import Any, AsyncIterator

from agents.claims_agent import ClaimsAgent

from .base import BaseGraphAgent


def _shape_run_result(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata", {}) or {}
    metadata["process_name"] = "claims_agent"
    return {
        "reply": result.get("reply", ""),
        "document_comment": result.get("document_comment", ""),
        "handled_by_agent": result.get("handled_by_agent", True),
        "document_created": result.get("document_created", False),
        "awaiting_input": result.get("awaiting_input", False),
        "current_agent": result.get("current_agent"),
        "task_completed": result.get("task_completed", False),
        "metadata": metadata,
        "error": result.get("error"),
    }


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
        return _shape_run_result(result)

    async def astream(
            self,
            message: str,
            thread_id: str,
            user_metadata: dict[str, Any] | None = None,
            document_type: str | None = None,
        ) -> AsyncIterator[dict[str, Any]]:
        """Стримит progress-события + финальный result."""
        user_metadata = user_metadata or {}
        async for event in self.agent.astream_user_message(
            message,
            thread_id,
            user_metadata=user_metadata,
            document_type=document_type or "lawsuit",
        ):
            if event.get("channel") == "result":
                yield {"channel": "result", "data": _shape_run_result(event["data"])}
            else:
                yield event
