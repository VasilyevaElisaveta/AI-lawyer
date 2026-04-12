from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """
    total=False  →  все поля опциональны на уровне TypedDict.
    В коде узлов используем state.get("field", default).
    """

    # ── Сообщения (для будущего диалогового intake) ───────────
    messages: Annotated[list, add_messages]

    # ── Управление памятью ────────────────────────────────────
    conversation_summary: str
    total_tokens: int

    # ── Тип генерируемого документа ───────────────────────────
    # "lawsuit" — исковое заявление (по умолчанию)
    # "pretrial_claim" — досудебная претензия
    # "contract" — договор
    doc_type: str

    # ── Входные данные ────────────────────────────────────────
    raw_input: str                  # свободный текст от пользователя
    input_data: dict[str, Any]      # структурированный ввод (от маршрутизатора)

    # ══════════════════════════════════════════════════════════
    #  Поля для ДОГОВОРА
    # ══════════════════════════════════════════════════════════

    party_a_info: str
    party_b_info: str
    contract_subject: str
    contract_terms: str
    governing_law: str
    contract_amount: float

    # Используем аналогичные поля, как для исков, но адаптированные для договора
    # Можно добавить специфические поля позже

    # ══════════════════════════════════════════════════════════
    #  Общие поля (для обоих типов документов)
    # ══════════════════════════════════════════════════════════

    # ── Результаты классификации ──────────────────────────────
    case_type: str                  # "civil" | "arbitration" (только для исков)
    case_category: str              # debt_collection, employment, consumer, ...

    # ── Валидация ─────────────────────────────────────────────
    validation_errors: list[str]
    validation_warnings: list[str]  # мягкие предупреждения (рекомендации)
    is_valid: bool
    response_to_user: str | None    # сообщение пользователю при недостающих данных

    # ── Правовое исследование ─────────────────────────────────
    applicable_laws: str
    legal_positions: str

    # ── Генерация ─────────────────────────────────────────────
    generated_documents: list[str]
    summarized_documents: list[str]

    # ── Проверка качества ─────────────────────────────────────
    qa_passed: bool
    qa_feedback: str
    qa_attempts: int

    # ── Финальный результат ───────────────────────────────────
    final_document: str
