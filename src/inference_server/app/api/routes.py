import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..schemas.chat import ChatRequest, ChatResponse
from ..services.agent_service import AgentService


logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def get_agent_service(request: Request):
    """Dependency injection для AgentService."""
    return request.app.state.agent_service


@router.get("/health", response_model=Dict[str, Any])
async def health():
    """Проверка здоровья сервера."""
    return {
        "status": "ok",
        "service": "AI-Lawyer Inference Server",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/invoke", response_model=ChatResponse)
async def invoke(
    request: ChatRequest,
    service: AgentService = Depends(get_agent_service)
):
    """
    Основной эндпоинт для обработки запросов через агентов.
    
    Args:
        request: ChatRequest с полями raw_input, thread_id и опциональным agent_type
        service: AgentService для обработки
        
    Returns:
        ChatResponse с ответом и метаданными
    """
    try:
        logger.info(f"Получен запрос: thread_id={request.thread_id}, agent_type={request.agent_type}")
        result = await service.process(request)
        logger.info(f"Запрос обработан успешно: {len(result.reply)} символов в ответе")
        return result
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )


@router.post("/invoke/{agent_type}", response_model=ChatResponse)
async def invoke_with_agent_type(
    agent_type: str,
    request: ChatRequest,
    service: AgentService = Depends(get_agent_service)
):
    """
    Эндпоинт для обработки запроса конкретным агентом.
    
    Args:
        agent_type: тип агента (contract, general, router)
        request: ChatRequest
        service: AgentService для обработки
        
    Returns:
        ChatResponse с ответом и метаданными
    """
    # Переопределяем agent_type из URL пути
    request.agent_type = agent_type
    try:
        logger.info(f"Получен запрос на агент: {agent_type}, thread_id={request.thread_id}")
        result = await service.process(request)
        logger.info(f"Запрос обработан успешно агентом {agent_type}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на {agent_type}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )

