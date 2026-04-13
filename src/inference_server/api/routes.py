from fastapi import APIRouter, Depends

from ..schemas.chat import ChatRequest, ChatResponse
from ..services.agent_service import AgentService

router = APIRouter()


def get_agent_service():
    return AgentService()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/invoke", response_model=ChatResponse)
async def invoke(
    request: ChatRequest,
    service: AgentService = Depends(get_agent_service)
):
    result = await service.process(request)
    return result
