import os
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM

from ...common.stream import emit_progress
from ...utils import update_tokens_metadata


ANSWER_STAGE = "answer"

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
