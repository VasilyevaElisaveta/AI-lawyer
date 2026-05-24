import json
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
            user_metadata: dict[str, Any] | None = None,
            input_data: dict[str, Any] | None = None,
            document_type: str | None = None,
        ) -> dict[str, Any]:
        user_metadata = user_metadata or {}
        if input_data:
            payload = dict(input_data)
            if document_type and "document_type" not in payload:
                payload["document_type"] = document_type
            message = json.dumps(payload, ensure_ascii=False)

        result = await self.agent.process_user_message(
            message,
            thread_id,
            user_metadata=user_metadata,
            document_type=document_type or "lawsuit",
        )
        status = result.get("status", "")
        task_completed = (
            result.get("document_created") is True
            and status == "completed"
        )
        return {
            "reply": result.get("reply", ""),
            "handled_by_agent": result.get("handled_by_agent", True),
            "document_created": result.get("document_created", False),
            "task_completed": task_completed,
            "metadata": result.get("metadata", {}),
            "error": result.get("error"),
        }
