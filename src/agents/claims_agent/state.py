"""
Определение ClaimsAgentState — единого состояния, которое проходит через все узлы LangGraph.
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class ClaimsAgentState(TypedDict, total=False):
    """
    total=False  →  все поля опциональны на уровне TypedDict.
    В коде узлов используем state.get("field", default).
    """

    # ── Сообщения (для будущего диалогового intake) ───────────
    messages: Annotated[list, add_messages]

    user_metadata: dict[str, Any]

    # ── Входные данные ────────────────────────────────────────
    raw_input: str                  # свободный текст от пользователя
    input_data: dict[str, Any]      # структурированный ввод (от маршрутизатора)

    # ── Метаданные запроса ────────────────────────────────────
    request_id: str                 # UUID для трассировки
    user_id: str                    # ID пользователя
    x_headers: dict[str, str]       # заголовки запроса

    # ── Тип генерируемого документа ───────────────────────────
    # "lawsuit"   — исковое заявление (по умолчанию)
    # "complaint" — досудебная претензия
    document_type: str

    # ── Извлечённые данные дела ────────────────────────────────
    plaintiff_info: str
    defendant_info: str
    third_parties_info: str
    court_info: str
    facts: str
    documents: str
    claims: str
    pretrial_settlement: str

    # ── Параметры претензии (специфичны для document_type=complaint) ──
    complaint_type: str             # "monetary" | "non_monetary"
    complaint_sphere: str           # "consumer" | "commercial" | "labor" | "other"
    complaint_sending_method: str   # "in_person" | "mail" | "electronic"
    complaint_response_deadline: int  # срок ответа в днях (обычно 15–30)
    complaint_deadline_basis: str   # основание срока (закон / договор)

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
    case_type: str                  # "civil" | "arbitration" | "administrative"
    case_category: str              # debt_collection, employment, consumer, ...
    is_property_dispute: bool       # DEPRECATED: используйте classification_data
    classification_data: dict[str, Any]  # Полная структура ClassificationResult

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
    final_document: str             # Текстовая версия документа
    document_path: str
    pipeline_status: str            # "in_progress" | "completed" | "completed_with_errors" | "failed"
    error: str                      # Описание ошибки (если есть)
