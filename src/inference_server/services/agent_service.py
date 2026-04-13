from .agents.contract_agent import ContractGraphAgent
from .agents.simple_agent import SimpleAgent
from .agents.router_agent import RouterAgent

from ..schemas.chat import ChatRequest, ChatResponse


class AgentService:
    def __init__(self):
        self.router = RouterAgent()
        self.contract_agent = ContractGraphAgent()
        self.simple_agent = SimpleAgent()

    async def process(self, request: ChatRequest) -> ChatResponse:
        # если явно указан агент
        if request.agent_type:
            agent = self._get_agent(request.agent_type)
            result = await agent.run(request.raw_input, request.thread_id)
            return self._to_response(result)

        # иначе через роутер
        route = await self.router.run(request.raw_input, request.thread_id)

        if route["route"] == "contract":
            result = await self.contract_agent.run(
                request.raw_input, request.thread_id
            )
        else:
            result = await self.simple_agent.run(
                request.raw_input, request.thread_id
            )

        return self._to_response(result)

    def _get_agent(self, agent_type: str):
        mapping = {
            "contract": self.contract_agent,
            "simple": self.simple_agent,
        }
        return mapping.get(agent_type, self.simple_agent)

    def _to_response(self, result: dict) -> ChatResponse:
        return ChatResponse(
            reply=result.get("reply", ""),
            handled_by_agent=result.get("handled_by_agent", True),
            document_created=result.get("document_created", False)
        )