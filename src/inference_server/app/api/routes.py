import os
from datetime import datetime
from typing import Dict, Any

from logger import LoggerFactory

from fastapi import APIRouter, Depends, HTTPException, status, Request

from ..schemas.chat import ChatRequest, ChatResponse, ChatNameRequest, ChatNameResponse
from ..services import AgentService, LLMService


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)
router = APIRouter(tags=["chat"])


def get_agent_service(request: Request):
    """Dependency injection for the AgentService"""
    return request.app.state.agent_service


def get_llm_service(request: Request):
    return request.app.state.llm_service


@router.get("/health", response_model=Dict[str, Any])
async def health():
    """Проверка здоровья сервера."""
    return {
        "status": "ok",
        "service": "AI-Lawyer Inference Server",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/chat_name", response_model=ChatNameResponse)
async def get_chat_name(
    request: ChatNameRequest,
    llm: LLMService = Depends(get_llm_service)
):
    try:
        result = await llm.aget_chat_name(request.raw_input)
        response = result.get("response", {})
        metadata = result.get("metadata", {})
        chat_name = response.content
        logger.debug(f"Got chat name: {chat_name}")
        return ChatNameResponse(
            thread_id=request.thread_id,
            chat_name=chat_name,
            latency_ms=metadata.get("latency_ms", 0),
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
            total_tokens=metadata.get("total_tokens", 0),
            run_id=metadata.get("run_id"),
            trace_id=metadata.get("trace_id"),
            process_name="llm_service"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )


@router.post("/invoke", response_model=ChatResponse)
async def ainvoke(
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
async def ainvoke_with_agent_type(
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

