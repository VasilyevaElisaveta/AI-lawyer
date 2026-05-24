from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict, Optional

from langgraph.graph.message import add_messages


class RouterAgentState(TypedDict, total=False):
    """
    Состояние маршрутизирующего агента.

    total=False → все поля опциональны на уровне TypedDict.
    В коде узлов используем state.get("field", default).
    """

    # ── Сообщения (для диалогового контекста) ─────────────
    messages: Annotated[list, add_messages]

    # ── Входные данные ────────────────────────────────────
    raw_input: Optional[str]

    # ── Активная задача (между сообщениями пользователя) ──
    current_agent: Optional[str]
    agent_fields: dict[str, Any]

    # ── Результаты классификации ──────────────────────────
    category: Literal["contract", "claim", "pretrial_claim", "general_question"]
    document_type: Optional[str]
    classification_confidence: float
    classification_result: dict[str, Any]

    # ── Проверка продолжения текущей задачи ───────────────
    continue_current_task: bool
    skip_classification: bool

    # ── Извлечение полей ────────────────────────────────────
    fields_complete: bool
    missing_fields_reply: Optional[str]

    # ── Статус реализации ──────────────────────────────────
    is_implemented: bool
    error: Optional[str]

    routed_to: Optional[str]

    usage_metadata: dict[str, Any]
