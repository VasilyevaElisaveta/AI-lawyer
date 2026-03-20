"""
Определение AgentState — единого состояния, которое проходит через все узлы LangGraph.
"""
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

    # ── Входные данные ────────────────────────────────────────
    raw_input: str                  # свободный текст от пользователя
    input_data: dict[str, Any]      # структурированный ввод (от маршрутизатора)

    # ── HTTP заголовки ─────────────────────────────────────────
    x_headers: dict[str, str]       # заголовки запроса

    # ── Извлечённые данные дела ────────────────────────────────
    plaintiff_info: str
    defendant_info: str
    third_parties_info: str
    court_info: str
    facts: str
    documents: str
    claims: str
    pretrial_settlement: str

    # ── Финансовые данные (вводимые пользователем) ─────────────
    principal_amount: float         # основной долг
    penalty_amount: float           # неустойка / пени
    interest_amount: float          # проценты по ст.395 ГК РФ
    moral_damage: float             # моральный вред
    court_expenses: float           # судебные расходы

    # ── Параметры для расчётов ────────────────────────────────
    penalty_rate: float             # дневная ставка неустойки
    penalty_start_date: str         # ДД.ММ.ГГГГ
    penalty_end_date: str
    interest_start_date: str
    interest_end_date: str
    cbr_key_rate: float             # ключевая ставка ЦБ (доля, напр. 0.16 = 16%)

    # ── Результаты классификации ──────────────────────────────
    case_type: str                  # "civil" | "arbitration"
    case_category: str              # debt_collection, employment, consumer, ...
    is_property_dispute: bool

    # ── Валидация ─────────────────────────────────────────────
    validation_errors: list[str]
    is_valid: bool
    validation_attempts: int

    # ── Правовое исследование ─────────────────────────────────
    applicable_laws: str
    legal_positions: str

    # ── Расчёты ───────────────────────────────────────────────
    state_duty: float               # госпошлина
    total_claim: float              # цена иска
    calculation_details: str        # текст расчёта для вставки в документ

    # ── Генерация ─────────────────────────────────────────────
    generated_document: str

    # ── Проверка качества ─────────────────────────────────────
    qa_passed: bool
    qa_feedback: str
    qa_attempts: int

    # ── Финальный результат ───────────────────────────────────
    final_document: str
    error: str