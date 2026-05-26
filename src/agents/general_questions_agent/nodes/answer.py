import os
import re
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM, SELF_INTRO_REPLY

from ...common.stream import emit_progress
from ...utils import update_tokens_metadata


ANSWER_STAGE = "answer"


# Паттерны для перехвата вопросов «о себе».
# GigaChat на стороне API подменяет ответ модели на собственный промо-текст
# (рекламу сервисов Сбера), игнорируя наш SystemMessage. Поэтому такие вопросы
# мы отлавливаем здесь и отвечаем готовым текстом из SELF_INTRO_REPLY без
# обращения к LLM.
_SELF_INTRO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bкто\s+ты\b"),
    re.compile(r"\bчто\s+(ты|вы)\s+(умеешь|умеете)\b"),
    re.compile(r"\bчто\s+(ты|вы)\s+(можешь|можете)\b"),
    re.compile(r"\bна\s+что\s+(ты|вы)\s+способ"),
    re.compile(r"\bрасскажи\s+(мне\s+)?(пожалуйста\s+)?о\s+себе\b"),
    re.compile(r"\bрасскажи\s+(мне\s+)?(пожалуйста\s+)?(,\s*)?что\s+(ты|вы)\s+умеешь\b"),
    re.compile(r"\bкакие\s+у\s+(тебя|вас)\s+(возможност|функци)"),
    re.compile(r"\bопиши\s+(свои|твои)\s+(возможност|функци)"),
    re.compile(r"\bпредставься\b"),
    re.compile(r"\bкак\s+с\s+тобой\s+работать\b"),
    re.compile(r"\bтвои\s+(возможност|функци)"),
    re.compile(r"\bчем\s+(ты|вы)\s+(можешь|можете)\s+помочь\b"),
)


def _looks_like_self_intro_question(text: str) -> bool:
    """Проверяет, является ли последний user-message вопросом «расскажи о себе»."""
    if not text:
        return False
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    return any(p.search(normalized) for p in _SELF_INTRO_PATTERNS)


def _last_user_text(history: list[BaseMessage]) -> str:
    for msg in reversed(history):
        if isinstance(msg, HumanMessage):
            return (msg.content or "").strip()
    return ""

logger = LoggerFactory.get_logger(
    name="GeneralQuestionsAgentAnswerNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def clear_before_end(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "raw_input": None,
    }


async def clear_previous_run_results(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": None,
        "reply": None,
    }


def _build_chat_messages(
    history: list[BaseMessage],
) -> list[BaseMessage]:
    """
    Собирает финальный список сообщений для LLM:
    - объединяет ANSWER_SYSTEM и накопленную сводку (если она лежит в начале
      `messages` как SystemMessage из memory_node) в один SystemMessage,
    - дальше идут только human/ai-сообщения.
    """
    summary_text = ""
    rest: list[BaseMessage] = list(history)
    if rest and isinstance(rest[0], SystemMessage):
        summary_text = (rest[0].content or "").strip()
        rest = rest[1:]

    parts = [ANSWER_SYSTEM.strip()]
    if summary_text:
        parts.append(summary_text)
    system_content = "\n\n".join(parts)

    return [SystemMessage(content=system_content), *rest]


async def answer_node(
    state: GeneralQuestionAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> Dict[str, Any]:
    """
    Отвечает на сообщение пользователя. Чанки ответа LLM по мере поступления
    публикуются в custom-канал графа через emit_progress(stage="answer").
    В режиме graph.invoke writer — no-op, поведение идентично прежнему.
    """
    logger.info("Start")
    history = list(state.get("messages") or [])
    if not history:
        return {
            "error": "[general_questions_agent] empty input",
        }

    # Hot-path для вопросов «расскажи о себе / что ты умеешь / кто ты».
    # GigaChat подменяет такие ответы на стороне API на свой заводской промо-текст,
    # игнорируя SystemMessage. Поэтому отвечаем сами, без LLM.
    last_user_text = _last_user_text(history)
    if _looks_like_self_intro_question(last_user_text):
        logger.info("Self-intro shortcut: skipping LLM, returning SELF_INTRO_REPLY")
        emit_progress(ANSWER_STAGE, SELF_INTRO_REPLY)
        return {
            "reply": SELF_INTRO_REPLY,
            "messages": [AIMessage(content=SELF_INTRO_REPLY)],
            "usage_metadata": state.get("usage_metadata", {}) or {},
        }

    chat_messages = _build_chat_messages(history)
    reply_parts: list[str] = []
    final_chunk = None

    try:
        async for chunk in llm.astream(chat_messages, config=config):
            piece = getattr(chunk, "content", "") or ""
            if piece:
                reply_parts.append(piece)
                emit_progress(ANSWER_STAGE, piece)
            final_chunk = chunk if final_chunk is None else final_chunk + chunk
    except Exception as e:
        logger.error(f"[general_questions_agent] astream error: {e}", exc_info=True)
        return {
            "error": "[general_questions_agent] astream error",
        }

    reply = "".join(reply_parts)
    if not reply and final_chunk is not None:
        reply = getattr(final_chunk, "content", "") or ""

    new_usage = getattr(final_chunk, "usage_metadata", None) or {}
    previous_usage_metadata = state.get("usage_metadata", {}) or {}
    usage_metadata = update_tokens_metadata(
        previous_usage_metadata,
        new_usage,
        ["input_tokens", "output_tokens", "total_tokens"],
    )

    logger.debug(f"Got result reply: {reply}")
    logger.info("Finish")
    return {
        "reply": reply,
        "messages": [AIMessage(content=reply)],
        "usage_metadata": usage_metadata,
    }
