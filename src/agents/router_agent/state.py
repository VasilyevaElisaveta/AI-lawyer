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
    raw_input: Optional[str]                  # свободный текст от пользователя

    # ── Результaты классификации ──────────────────────────
    category: Literal["contract", "lawsuit", "pretrial_claim", "general_question"]
    classification_confidence: float  # уверенность в классификации (0.0 - 1.0)
    classification_result: dict[str, Any]  # полный результат от LLM

    # ── Статус реализации ──────────────────────────────────
    is_implemented: bool             # реализован ли обработчик для категории
    error: Optional[str]

    routed_to: Optional[str]                   # куда направлен запрос: "contract_agent", "lawsuit_agent", "pretrial_claim_agent", "general_question_agent", None
    
    usage_metadata: Optional[dict[str, Any]]