import json
import os
from datetime import datetime
from typing import Dict, Any

from logger import LoggerFactory

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from ..schemas.chat import (
    ChatAgentRequest,
    ChatRequest,
    ChatResponse,
    ChatNameRequest,
    ChatNameResponse,
)
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
    service: AgentService = Depends(get_agent_service),
):
    """
    Основной эндпоинт: маршрутизация через router и активные сессии агентов.
    Выбор агента в теле запроса не поддерживается — только /invoke/{{agent_type}}.
    """
    try:
        logger.info(f"Получен запрос: thread_id={request.thread_id}")
        result = await service.process_routed(request)
        logger.info(f"Запрос обработан успешно: {len(result.reply)} символов в ответе")
        return result
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}",
        )


def _ndjson_stream(events_iter):
    """Оборачивает async-итератор словарей в NDJSON-поток для StreamingResponse."""
    async def generator():
        try:
            async for event in events_iter:
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as exc:
            logger.error("Ошибка стриминга: %s", exc, exc_info=True)
            yield json.dumps(
                {"type": "error", "message": f"Внутренняя ошибка стриминга: {exc}"},
                ensure_ascii=False,
            ) + "\n"

    return generator()


@router.post("/invoke/stream")
async def ainvoke_stream(
    request: ChatRequest,
    service: AgentService = Depends(get_agent_service),
):
    """
    Стриминговый аналог /invoke. Возвращает NDJSON-поток событий:
      - {"type": "progress", "stage": "pre_generation"|"post_generation"|"answer",
         "content": "...", "document_type": "..."}
      - {"type": "result", "reply": "...", "final_reply_text": "...", ...}
      - {"type": "error",  "message": "..."}

    Для claims_agent stage = pre_generation / post_generation (статус-сообщения
    «приступаю к генерации» и итоговое после DOCX).
    Для general_questions_agent stage = answer (потоковые токены ответа LLM).
    Для contract_agent промежуточных событий пока нет — приходит только result.
    """
    logger.info(f"Stream-запрос: thread_id={request.thread_id}")
    events = service.process_routed_stream(request)
    return StreamingResponse(
        _ndjson_stream(events),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.post("/invoke/{agent_type}/stream")
async def ainvoke_with_agent_type_stream(
    agent_type: str,
    request: ChatAgentRequest,
    service: AgentService = Depends(get_agent_service),
):
    """
    Стриминговый аналог /invoke/{agent_type}. Формат событий тот же,
    что у /invoke/stream. Промежуточные события приходят для claims_agent
    (pre_generation/post_generation) и general_questions_agent (answer).
    """
    resolved = service.resolve_agent_type(agent_type)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Неизвестный агент: {agent_type}. "
                "Доступны: claims_agent, contract_agent, general_questions_agent, router_agent"
            ),
        )
    logger.info(f"Stream-запрос на агент {resolved}, thread_id={request.thread_id}")
    events = service.process_with_agent_stream(resolved, request)
    return StreamingResponse(
        _ndjson_stream(events),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.post("/invoke/{agent_type}", response_model=ChatResponse)
async def ainvoke_with_agent_type(
    agent_type: str,
    request: ChatAgentRequest,
    service: AgentService = Depends(get_agent_service),
):
    """
    Прямой вызов указанного агента.
    agent_type в path: claims_agent, contract_agent, general_questions_agent, router_agent.
    request_metadata — параметры вызова (например document_type для claims_agent).
    """
    resolved = service.resolve_agent_type(agent_type)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Неизвестный агент: {agent_type}. "
                "Доступны: claims_agent, contract_agent, general_questions_agent, router_agent"
            ),
        )
    try:
        logger.info(f"Получен запрос на агент: {resolved}, thread_id={request.thread_id}")
        result = await service.process_with_agent(resolved, request)
        logger.info(f"Запрос обработан успешно агентом {resolved}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на {resolved}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке запроса: {str(e)}",
        )