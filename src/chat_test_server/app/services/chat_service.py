from uuid import UUID, uuid4

from ..schemas.chat import ChatRequest, ChatResponse
from ..services.agent_client import AgentClient


class ChatService:
    def __init__(self, agent_client: AgentClient) -> None:
        self._agent_client = agent_client

    async def chat(self, request: ChatRequest) -> ChatResponse:
        conversation_id: UUID = request.conversation_id or uuid4()
        reply = await self._agent_client.send_message(
            message=request.message,
            conversation_id=str(conversation_id),
        )
        return ChatResponse(
            conversation_id=conversation_id,
            message=request.message,
            reply=reply,
        )