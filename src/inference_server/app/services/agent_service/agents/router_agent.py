from typing import Any

from agents.router_agent import RouterAgent

from .base import BaseGraphAgent


class RouterGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = RouterAgent(llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        result = await self.agent.process_user_message(message, thread_id)
        response = result.get("response", {})
        metadata = result.get("metadata", {})
        metadata["process_name"] = "router_agent"
        error = response.get("error", None)
        routed_to = response.get("routed_to", None)
        fields_complete = response.get("fields_complete", False)
        missing_fields_reply = response.get("missing_fields_reply")

        return {
            "routed_to": routed_to,
            "error": error,
            "handled_by_agent": True,
            "metadata": metadata,
            "fields_ready": bool(fields_complete),
            "reply": missing_fields_reply,
            "input_data": response.get("agent_fields"),
            "document_type": response.get("document_type"),
        }

    async def clear_current_agent(self, thread_id: str) -> None:
        await self.agent.clear_current_agent(thread_id)
