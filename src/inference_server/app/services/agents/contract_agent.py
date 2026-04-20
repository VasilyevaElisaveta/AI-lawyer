from typing import Any

from .base import BaseGraphAgent

from .....agents.contract_agent import ContractAgent


class ContractGraphAgent(BaseGraphAgent):
    def __init__(self, llm):
        self.agent = ContractAgent(llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        return await self.agent.process_user_message(message, thread_id)