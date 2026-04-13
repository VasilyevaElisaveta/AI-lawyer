from .base import BaseGraphAgent


class SimpleAgent(BaseGraphAgent):
    async def run(self, message: str, thread_id: str):
        return {
            "reply": f"Echo: {message}",
            "handled_by_agent": True,
            "document_created": False
        }