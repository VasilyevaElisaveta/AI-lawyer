from typing import Any

from agents.contract_agent import ContractAgent

from .base import BaseGraphAgent


class ContractGraphAgent(BaseGraphAgent):
    def __init__(self, llm, generator_llm=None):
        self.agent = ContractAgent(llm, generator_llm=generator_llm)

    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        return await self.agent.process_user_message(message, thread_id)