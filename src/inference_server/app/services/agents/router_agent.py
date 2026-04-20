from typing import Any

from .base import BaseGraphAgent

from .....agents.router_agent import RouterAgent


class RouterGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = RouterAgent(llm)
    
    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        result = await self.agent.process_user_message(message, thread_id)
        category = result.get("routed_to", "general_question")
        return {
            "routed_to": result.get(category, "general_agent"),
            "classification_confidence": result.get("classification_confidence", 0.0),
            "handled_by_agent": True,
        }