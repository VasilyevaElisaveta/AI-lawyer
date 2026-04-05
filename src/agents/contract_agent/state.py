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

    # ── Тип генерируемого документа ───────────────────────────
    # "lawsuit" — исковое заявление (по умолчанию)
    # "pretrial_claim" — досудебная претензия
    # "contract" — договор
    doc_type: str

    # ── Входные данные ────────────────────────────────────────
    raw_input: str                  # свободный текст от пользователя
    input_data: dict[str, Any]      # структурированный ввод (от маршрутизатора)

    # ══════════════════════════════════════════════════════════
    #  Поля для ИСКОВОГО ЗАЯВЛЕНИЯ
    # ══════════════════════════════════════════════════════════

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

    # ── Проценты за пользование займом (ст. 809 ГК РФ) ────────
    loan_interest_rate: float       # годовая ставка (доля: 0.10 = 10%)
    loan_interest_amount: float     # рассчитанная сумма
    loan_start_date: str            # дата выдачи займа / начала начисления
    loan_end_date: str              # дата расчёта (подачи иска)

    # ── Параметры для расчёта неустойки ───────────────────────
    penalty_rate: float             # дневная ставка неустойки (доля, напр. 0.001 = 0.1%)
    penalty_start_date: str         # ДД.ММ.ГГГГ
    penalty_end_date: str

    # ── Параметры для расчёта процентов по ст. 395 ────────────
    interest_start_date: str
    interest_end_date: str
    cbr_key_rate: float             # ключевая ставка ЦБ (доля, напр. 0.16 = 16%)

    # ── Флаги для просительной части ──────────────────────────
    request_ongoing_penalty: bool   # неустойка по день факт. исполнения
    request_ongoing_interest: bool  # проценты по день факт. исполнения

    # ══════════════════════════════════════════════════════════
    #  Поля для ДОСУДЕБНОЙ ПРЕТЕНЗИИ
    # ══════════════════════════════════════════════════════════

    sender_info: str                # отправитель претензии
    recipient_info: str             # получатель претензии
    claim_type: str                 # тип претензии (возврат долга, товар, услуга...)
    basis: str                      # основание (номер/дата договора, чека, акта)
    sender_demands: str             # требования отправителя
    response_deadline: str          # срок для добровольного удовлетворения
    total_amount: float             # итого по претензии (без госпошлины)
    supporting_documents: str       # документы-подтверждения

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
    validation_attempts: int

    # ── Правовое исследование ─────────────────────────────────
    applicable_laws: str
    legal_positions: str

    # ── Расчёты ───────────────────────────────────────────────
    state_duty: float               # госпошлина (только для исков)
    total_claim: float              # цена иска (только для исков)
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
