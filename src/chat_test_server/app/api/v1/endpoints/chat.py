from fastapi import APIRouter, Depends, Request

from ....schemas.chat import ChatRequest, ChatResponse
from ....services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


@router.post("", response_model=ChatResponse)
async def send_chat_message(
    request_body: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return await chat_service.chat(request_body)