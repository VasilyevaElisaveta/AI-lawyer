"""
Модуль расчётов(Заглушка).

═══════════════════════════════════════════════════════════════════
  Этот модуль содержит заглушки для всех расчётов.
  Реальная логика расчётов пока НЕ реализована.

  ЧТО НУЖНО СДЕЛАТЬ:
  1. Реализовать calc_state_duty_civil()     — госпошлина
  2. Реализовать calc_state_duty_arbitration() — госпошлина 
  3. Реализовать calc_penalty()               — неустойка 
  4. Реализовать calc_interest_395()          — проценты
  5. Реализовать calc_loan_interest()         — проценты за пользование
  6. Учесть особенности потребительских споров (ЗоЗПП)
  7. Написать тесты в tests/test_calculator.py

  СЕЙЧАС:
  Модуль просто пробрасывает входные суммы и формирует текстовый расчёт.
  Госпошлина ставится 0 с пометкой [РАССЧИТАТЬ].
═══════════════════════════════════════════════════════════════════

Поддерживает два типа документов:
  • lawsuit        — исковое заявление (с госпошлиной)
  • pretrial_claim — досудебная претензия (без госпошлины)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def calculator_node(state: AgentState) -> dict[str, Any]:
    """
    Узел графа: математические расчёты.

    Сейчас — заглушка: пробрасывает входные суммы, формирует
    текстовый расчёт, помечает нереализованные места [РАССЧИТАТЬ].
    """
    logger.info("▶ Calculator node started (STUB)")

    doc_type = state.get("doc_type", "lawsuit")
    principal = _to_float(state.get("principal_amount", 0))
    penalty = _to_float(state.get("penalty_amount", 0))
    interest = _to_float(state.get("interest_amount", 0))
    loan_interest = _to_float(state.get("loan_interest_amount", 0))
    moral = _to_float(state.get("moral_damage", 0))
    expenses = _to_float(state.get("court_expenses", 0))
    is_property = state.get("is_property_dispute", False)
    case_type = state.get("case_type", "civil")

    details: list[str] = ["РАСЧЁТ ТРЕБОВАНИЙ", ""]
    section = 1

    # ── 1. Проценты за пользование займом (ст. 809 ГК РФ) ─────
    #
    # TODO: Реализовать calc_loan_interest()
    #   Формула: principal × rate / 365 × days
    #
    loan_rate = _to_float(state.get("loan_interest_rate", 0))
    loan_start = state.get("loan_start_date", "")
    loan_end = state.get("loan_end_date", "")

    if loan_rate > 0 and loan_start and loan_end:
        try:
            days = _days_between(loan_start, loan_end)
            # ЗАГЛУШКА: простой расчёт, 365 дней в году
            loan_interest = round(principal * loan_rate / 365 * days, 2)
            details.append(f"{section}. Проценты за пользование займом (ст. 809 ГК РФ):")
            details.append(
                f"   {_fmt(principal)} руб. × {loan_rate * 100:.2f}% / 365 × {days} дн. "
                f"= {_fmt(loan_interest)} руб."
            )
            details.append(f"   Период: с {loan_start} по {loan_end} ({days} дн.)")
            details.append(f"   [!] Расчёт упрощённый — требуется проверка")
            details.append("")
            section += 1
        except ValueError as e:
            logger.warning("Loan interest calc error: %s", e)

    # ── 2. Неустойка ──────────────────────────────────────────
    #
    # TODO: Реализовать calc_penalty()
    #   Формула: principal × daily_rate × days
    #
    penalty_rate = _to_float(state.get("penalty_rate", 0))
    pen_start = state.get("penalty_start_date", "")
    pen_end = state.get("penalty_end_date", "")

    if penalty_rate > 0 and pen_start and pen_end:
        try:
            days = _days_between(pen_start, pen_end)
            # ЗАГЛУШКА: простой расчёт
            penalty = round(principal * penalty_rate * days, 2)
            details.append(f"{section}. Неустойка за просрочку:")
            details.append(
                f"   {_fmt(principal)} руб. × {penalty_rate * 100:.4g}% × {days} дн. "
                f"= {_fmt(penalty)} руб."
            )
            details.append(f"   Период: с {pen_start} по {pen_end} ({days} дн.)")
            details.append(f"   [!] Расчёт упрощённый — требуется проверка")
            details.append("")
            section += 1
        except ValueError as e:
            logger.warning("Penalty calc error: %s", e)

    # ── 3. Проценты по ст. 395 ГК РФ ─────────────────────────
    #
    # TODO: Реализовать calc_interest_395()
    #   Формула для каждого периода: principal × rate / 365 × day
    #
    cbr_rate = _to_float(state.get("cbr_key_rate", 0))
    int_start = state.get("interest_start_date", "")
    int_end = state.get("interest_end_date", "")

    if cbr_rate > 0 and int_start and int_end:
        try:
            days = _days_between(int_start, int_end)
            # ЗАГЛУШКА: одна ставка на весь период
            interest = round(principal * cbr_rate / 365 * days, 2)
            details.append(f"{section}. Проценты по ст. 395 ГК РФ:")
            details.append(
                f"   {_fmt(principal)} руб. × {cbr_rate * 100:.2f}% / 365 × {days} дн. "
                f"= {_fmt(interest)} руб."
            )
            details.append(f"   Период: с {int_start} по {int_end} ({days} дн.)")
            details.append(f"   [!] ВНИМАНИЕ: использована единая ставка {cbr_rate * 100:.2f}%.")
            details.append(f"   [!] Для точного расчёта нужно разбить на периоды по изменениям ключевой ставки ЦБ.")
            details.append("")
            section += 1
        except ValueError as e:
            logger.warning("Interest calc error: %s", e)

    # ── 4. Итого сумма требований ─────────────────────────────
    claim_total = principal + loan_interest + penalty + interest + moral
    price_for_claim = principal + loan_interest + penalty + interest  # цена иска (без морального)

    details.append(f"{section}. Итого сумма требований:")
    components = []
    if principal:
        components.append(f"основной долг {_fmt(principal)} руб.")
    if loan_interest:
        components.append(f"проценты за пользование {_fmt(loan_interest)} руб.")
    if penalty:
        components.append(f"неустойка {_fmt(penalty)} руб.")
    if interest:
        components.append(f"проценты по ст. 395 {_fmt(interest)} руб.")
    if moral:
        components.append(f"моральный вред {_fmt(moral)} руб.")
    details.append("   " + " + ".join(components) + f" = {_fmt(claim_total)} руб.")
    details.append("")
    section += 1

    # ── 5. Госпошлина (ТОЛЬКО для исков) ──────────────────────
    #
    # TODO: Реализовать calc_state_duty_civil() и calc_state_duty_arbitration()
    #
    duty = 0.0
    if doc_type == "lawsuit":
        # ЗАГЛУШКА: госпошлина = 0 с пометкой
        duty = 0.0
        details.append(f"{section}. Государственная пошлина:")
        details.append(f"   [РАССЧИТАТЬ] — модуль расчёта госпошлины не реализован")
        if is_property and price_for_claim > 0:
            article = "333.21" if case_type == "arbitration" else "333.19"
            details.append(f"   Применимая норма: ст. {article} НК РФ")
            details.append(f"   База для расчёта (цена иска): {_fmt(price_for_claim)} руб.")
        else:
            details.append(f"   Неимущественный иск")
        details.append("")
        section += 1

    # ── 6. Ongoing (по день фактического исполнения) ──────────
    ongoing_parts = []
    if state.get("request_ongoing_penalty") and penalty_rate > 0:
        ongoing_parts.append(
            f"Неустойка в размере {penalty_rate * 100:.4g}% от суммы долга "
            f"{_fmt(principal)} руб. за каждый день просрочки, начиная с "
            f"{pen_end} по день фактического исполнения обязательства"
        )
    if state.get("request_ongoing_interest") and loan_rate > 0:
        ongoing_parts.append(
            f"Проценты за пользование займом по ставке {loan_rate * 100:.2f}% годовых "
            f"на сумму {_fmt(principal)} руб., начиная с {loan_end} по день "
            f"фактического возврата суммы займа"
        )
    if ongoing_parts:
        details.append(f"{section}. Также по день фактического исполнения:")
        for p in ongoing_parts:
            details.append(f"   • {p}")
        details.append("")

    # ── Результат ─────────────────────────────────────────────
    result = {
        "loan_interest_amount": loan_interest,
        "penalty_amount": penalty,
        "interest_amount": interest,
        "state_duty": duty,
        "total_claim": price_for_claim,     # цена иска (для исков, без морального вреда)
        "total_amount": claim_total,        # итого (для претензий, с моральным)
        "calculation_details": "\n".join(details),
    }

    logger.info(
        "  [%s] STUB: claim_total=%.2f  price_for_claim=%.2f  duty=%.2f",
        doc_type,
        claim_total,
        price_for_claim,
        duty,
    )
    return result


# ═══════════════════════════════════════════════════════════════
#  ЗАГЛУШКИ ГОСПОШЛИНЫ
#  TODO: Реализовать реальные расчёты
# ═══════════════════════════════════════════════════════════════

def calc_state_duty_civil(claim: float) -> float:
    """
    ЗАГЛУШКА.
    Имущественный иск → суд общей юрисдикции.
    Ст. 333.19 НК РФ.

    TODO: Реализовать по шкале:
      до 20 000       → 4%, мин. 400
      20 001–100 000  → 800 + 3%
      100 001–200 000 → 3 200 + 2%
      200 001–1 000 000 → 5 200 + 1%
      свыше 1 000 000 → 13 200 + 0.5%, макс. 60 000
    """
    logger.warning("calc_state_duty_civil() is a STUB — returning 0")
    return 0.0


def calc_state_duty_arbitration(claim: float) -> float:
    """
    ЗАГЛУШКА.
    Имущественный иск → арбитражный суд.
    Ст. 333.21 НК РФ.

    TODO: Реализовать по шкале:
      до 100 000       → 4%, мин. 2 000
      100 001–200 000  → 4 000 + 3%
      200 001–1 000 000 → 7 000 + 2%
      1 000 001–2 000 000 → 23 000 + 1%
      свыше 2 000 000  → 33 000 + 0.5%, макс. 200 000
    """
    logger.warning("calc_state_duty_arbitration() is a STUB — returning 0")
    return 0.0


def calc_state_duty_non_property(case_type: str) -> float:
    """
    ЗАГЛУШКА.
    Неимущественный иск.

    TODO: Реализовать:
      СОЮ:  300 руб. (физлицо) / 6 000 руб. (юрлицо)
      Арбитраж: 6 000 руб.
    """
    logger.warning("calc_state_duty_non_property() is a STUB — returning 0")
    return 0.0


# ═══════════════════════════════════════════════════════════════
#  Утилиты (парсинг дат, форматирование)
# ═══════════════════════════════════════════════════════════════

_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y")


def parse_date(s: str) -> date:
    """Парсинг даты из нескольких распространённых форматов."""
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Неизвестный формат даты: «{s}»")


def _days_between(start_str: str, end_str: str) -> int:
    """Количество дней между двумя датами."""
    d1 = parse_date(start_str)
    d2 = parse_date(end_str)
    delta = (d2 - d1).days
    if delta < 0:
        raise ValueError(f"Начало ({start_str}) позже конца ({end_str})")
    return delta


def _to_float(value: Any) -> float:
    """Безопасное преобразование значения в float."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        cleaned = re.sub(r"[^\d.,]", "", value)
        cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _fmt(value: float) -> str:
    """Форматирование суммы: 1 234 567.89"""
    if value == int(value):
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")