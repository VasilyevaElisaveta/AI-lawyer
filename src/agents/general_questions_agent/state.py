from typing import Annotated, TypedDict, Optional, Any

from langgraph.graph.message import add_messages


class GeneralQuestionAgentState(TypedDict, total=False):
    """
    Состояние агента общих вопросов.
    
    total=False → все поля опциональны на уровне TypedDict.
    В коде узлов используем state.get("field", default).
    """

    # ── Сообщения (для диалогового контекста) ─────────────
    messages: Annotated[list, add_messages]
    conversation_summary: str

    # ── Входные данные ────────────────────────────────────
    raw_input: Optional[str]                  # вопрос пользователя

    # ── Финальный результат ────────────────────────────────
    reply: Optional[str]                      # ответ пользователю
    error: Optional[str]
    usage_metadata: dict[str, Any]