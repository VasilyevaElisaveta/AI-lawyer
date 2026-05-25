"""
Общая обёртка над custom-каналом LangGraph.

В обоих режимах (graph.ainvoke / graph.astream) узлы вызывают одну и ту же
функцию `emit_progress`. При invoke writer оказывается no-op и узел работает
без побочных эффектов; при astream(stream_mode=["custom", ...]) событие
прокидывается наружу клиенту.

Контракт события одинаковый для всех агентов:
    {
        "type":         "progress",
        "stage":        "<stage-name>",  # e.g. pre_generation | document_comment | answer
        "content":      "<текст>",
        "document_type": "lawsuit" | "complaint" | None,
    }
"""
from typing import Any, Callable


PROGRESS_EVENT_TYPE = "progress"


def _resolve_writer() -> Callable[[dict[str, Any]], None]:
    """Получает writer для custom-канала или no-op, если контекст недоступен."""
    try:
        from langgraph.config import get_stream_writer  # type: ignore
    except ImportError:
        try:
            from langgraph.types import get_stream_writer  # type: ignore
        except ImportError:
            return lambda _payload: None
    try:
        return get_stream_writer()
    except Exception:
        return lambda _payload: None


def emit_progress(
    stage: str,
    content: str,
    *,
    document_type: str | None = None,
) -> None:
    """Публикует прогресс-событие в custom-канал LangGraph (или no-op)."""
    if not content:
        return
    writer = _resolve_writer()
    writer(
        {
            "type": PROGRESS_EVENT_TYPE,
            "stage": stage,
            "content": content,
            "document_type": document_type,
        }
    )
