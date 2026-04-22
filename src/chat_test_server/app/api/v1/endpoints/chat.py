from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from ....schemas.chat import ChatRequest, ChatResponse
from ....services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


@router.post("")
async def send_chat_message(
    request_body: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    result = await chat_service.chat(request_body)

    if result.document_created:
        if not result.document_bytes:
            return JSONResponse(
                status_code=502,
                content={"detail": "document_created=true, but document bytes are missing or invalid"},
            )

        headers = {
            "Content-Disposition": f'attachment; filename="{result.document_filename}"',
            "X-Conversation-Id": str(result.conversation_id),
            "X-Document-Created": "true",
        }

        return Response(
            content=result.document_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers,
        )

    return ChatResponse(
        conversation_id=result.conversation_id,
        message=result.message,
        reply=result.reply or "",
        document_created=False,
    )