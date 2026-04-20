from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class GeneralQuestionAgentState(TypedDict, total=False):
    """
    Состояние агента общих вопросов.
    
    total=False → все поля опциональны на уровне TypedDict.
    В коде узлов используем state.get("field", default).
    """

    # ── Сообщения (для диалогового контекста) ─────────────
    messages: Annotated[list, add_messages]

    # ── Входные данные ────────────────────────────────────
    raw_input: str                  # вопрос пользователя

    # ── Финальный результат ────────────────────────────────
    reply: str                      # ответ пользователю
