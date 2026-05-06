from typing import Any

from .base import BaseGraphAgent

from .....agents.router_agent import RouterAgent


class RouterGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = RouterAgent(llm)
    
    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        result = await self.agent.process_user_message(message, thread_id)
        error = result.get("error", None)
        routed_to = result.get("routed_to", None)
        return {
            "routed_to": routed_to,
            "error": error,
            "handled_by_agent": True,
        }