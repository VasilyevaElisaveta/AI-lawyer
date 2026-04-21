from uuid import UUID, uuid4
import base64

from ..schemas.chat import ChatRequest, ChatResponse
from ..services.agent_client import AgentClient, InferenceResponse


class ChatService:
    def __init__(self, agent_client: AgentClient) -> None:
        self._agent_client = agent_client

    async def chat(self, request: ChatRequest) -> ChatResponse:
        conversation_id: UUID = request.conversation_id or uuid4()

        inference_reply: InferenceResponse = await self._agent_client.send_message(
            message=request.message,
            conversation_id=str(conversation_id),
        )

        raw = (inference_reply.reply or "").strip()
        is_docx = raw.startswith("UEsDB")
        if is_docx:
            raw = raw.replace("\n", "").replace("\r", "")
            document_bytes = base64.b64decode(raw)
            return ChatResponse(
                conversation_id=conversation_id,
                message=request.message,
                document_created=True,
                document_bytes=document_bytes,
                document_filename=f"{conversation_id}.docx",
            )
        return ChatResponse(
            conversation_id=conversation_id,
            message=request.message,
            reply=inference_reply.reply,
            document_created=False,
        )