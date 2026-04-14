from .base import BaseGraphAgent

from .....agents.router_agent import RouterAgent


class RouterGraphAgent(BaseGraphAgent):
    def __init__(self):
        self.agent = RouterAgent()
    
    async def run(self, message: str, thread_id: str):
        # TODO: здесь будет LangGraph router
        if "договор" in message.lower():
            return {"route": "contract"}
        return {"route": "simple"}