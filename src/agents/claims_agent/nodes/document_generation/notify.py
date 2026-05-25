"""
Промежуточные «статусные» узлы графа:

- pre_generation_notify_node — после успешной валидации формирует короткое сообщение
  «приступаю к генерации» с перечислением распознанных параметров.
- final_reply_node — после сохранения DOCX формирует итоговое сообщение со списком
  следующих шагов пользователя.

Сообщения, помимо записи в state, дополнительно публикуются в custom-канал LangGraph
через get_stream_writer(). В режиме graph.invoke writer — no-op, поэтому узлы
работают одинаково в обоих режимах (invoke и astream).
"""
import os
from typing import Any

from logger import LoggerFactory

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ...state import ClaimsAgentState
from ...prompts import (
    FINAL_REPLY_HUMAN,
    FINAL_REPLY_SYSTEM,
    PRE_GENERATION_HUMAN,
    PRE_GENERATION_SYSTEM,
    render_template,
)

from ....common.stream import emit_progress
from ....utils import messages_to_str, update_tokens_metadata


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


PRE_GENERATION_STAGE = "pre_generation"
POST_GENERATION_STAGE = "post_generation"


def _document_label(document_type: str) -> str:
    return "досудебная претензия" if document_type == "complaint" else "исковое заявление"


def _sending_method_label(method: str) -> str:
    return {
        "in_person": "лично, под подпись",
        "mail": "заказным письмом с уведомлением",
        "electronic": "электронно (email/ЭДО)",
    }.get(method or "", "—")


async def pre_generation_notify_node(
    state: ClaimsAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """LLM-сообщение «данные собраны, приступаю к генерации» + custom-event."""
    document_type = state.get("document_type", "lawsuit")
    logger.info(f"[claims][pre_generation] формирование статус-сообщения (doc={document_type})")

    prompt_text = render_template(
        PRE_GENERATION_HUMAN,
        {
            "document_type_label": _document_label(document_type),
            "plaintiff_info": state.get("plaintiff_info", "") or "—",
            "defendant_info": state.get("defendant_info", "") or "—",
            "claims": state.get("claims", "") or "—",
            "total_claim": state.get("total_claim") or 0,
            "principal_amount": state.get("principal_amount") or 0,
        },
    )

    usage_metadata = state.get("usage_metadata", {}) or {}
    text = ""
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=PRE_GENERATION_SYSTEM),
                HumanMessage(content=prompt_text),
            ],
            config=config,
        )
        text = (response.content or "").strip()
        usage_metadata = update_tokens_metadata(
            usage_metadata,
            getattr(response, "usage_metadata", {}) or {},
        )
    except Exception as exc:
        logger.warning("[claims][pre_generation] ошибка LLM: %s", exc)
        text = (
            f"Данные приняты. Приступаю к составлению документа: "
            f"{_document_label(document_type)}."
        )

    emit_progress(PRE_GENERATION_STAGE, text, document_type=document_type)

    return {
        "pre_generation_message": text,
        "usage_metadata": usage_metadata,
    }


async def final_reply_node(
    state: ClaimsAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """Итоговое LLM-сообщение пользователю после успешной генерации DOCX."""
    document_type = state.get("document_type", "lawsuit")
    logger.info("[claims][final_reply] формирование итогового сообщения (doc=%s)", document_type)

    history_text = messages_to_str(state.get("messages") or [])
    if len(history_text) > 4000:
        history_text = history_text[-4000:]

    prompt_text = render_template(
        FINAL_REPLY_HUMAN,
        {
            "document_type_label": _document_label(document_type),
            "plaintiff_info": state.get("plaintiff_info", "") or "—",
            "defendant_info": state.get("defendant_info", "") or "—",
            "court_info": state.get("court_info", "") or "—",
            "claims": state.get("claims", "") or "—",
            "total_claim": state.get("total_claim") or 0,
            "state_duty": state.get("state_duty") or 0,
            "sending_method_label": _sending_method_label(
                state.get("complaint_sending_method", "")
            ),
            "response_deadline": state.get("complaint_response_deadline") or "—",
            "conversation_history": history_text or "—",
        },
    )

    usage_metadata = state.get("usage_metadata", {}) or {}
    text = ""
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=FINAL_REPLY_SYSTEM),
                HumanMessage(content=prompt_text),
            ],
            config=config,
        )
        text = (response.content or "").strip()
        usage_metadata = update_tokens_metadata(
            usage_metadata,
            getattr(response, "usage_metadata", {}) or {},
        )
    except Exception as exc:
        logger.warning(f"[claims][final_reply] ошибка LLM: {exc}")
        text = (
            f"{_document_label(document_type).capitalize()} сформирован и сохранён. "
            "Проверьте реквизиты сторон и при необходимости вернитесь с уточнениями."
        )

    emit_progress(POST_GENERATION_STAGE, text, document_type=document_type)

    return {
        "final_reply_text": text,
        "messages": [AIMessage(content=text)],
        "usage_metadata": usage_metadata,
    }
