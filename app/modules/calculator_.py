"""
Модуль расчётов.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from app.core.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def calculator_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: математические расчёты."""
    logger.info("Calculator node started")

    principal = _to_float(state.get("principal_amount", 0))
    penalty = _to_float(state.get("penalty_amount", 0))
    interest = _to_float(state.get("interest_amount", 0))
    moral = _to_float(state.get("moral_damage", 0))
    expenses = _to_float(state.get("court_expenses", 0))
    is_property = state.get("is_property_dispute", False)
    case_type = state.get("case_type", "civil")

    details_lines: list[str] = ["РАСЧЁТ ИСКОВЫХ ТРЕБОВАНИЙ", ""]

    # ── 1. Неустойка (если надо рассчитать) ───────────────────
    penalty_rate = _to_float(state.get("penalty_rate", 0))
    pen_start = state.get("penalty_start_date", "")
    pen_end = state.get("penalty_end_date", "")

    if penalty_rate > 0 and pen_start and pen_end:
        try:
            days = _days_between(pen_start, pen_end)
            calculated_penalty = round(principal * penalty_rate * days, 2)
            penalty = calculated_penalty
            details_lines.append("1. Расчёт неустойки:")
            details_lines.append(
                f"   {_fmt(principal)} руб. × {penalty_rate * 100:.4g}% × {days} дн. "
                f"= {_fmt(calculated_penalty)} руб."
            )
            details_lines.append("")
        except ValueError as e:
            logger.warning("Penalty calc error: %s", e)

    # ── 2. Проценты по ст. 395 ГК РФ ─────────────────────────
    cbr_rate = _to_float(state.get("cbr_key_rate", 0))
    int_start = state.get("interest_start_date", "")
    int_end = state.get("interest_end_date", "")

    if cbr_rate > 0 and int_start and int_end:
        try:
            days = _days_between(int_start, int_end)
            calculated_interest = round(principal * cbr_rate / 365 * days, 2)
            interest = calculated_interest
            details_lines.append("2. Расчёт процентов по ст. 395 ГК РФ:")
            details_lines.append(
                f"   {_fmt(principal)} руб. × {cbr_rate * 100:.2f}% / 365 × {days} дн. "
                f"= {_fmt(calculated_interest)} руб."
            )
            details_lines.append("")
        except ValueError as e:
            logger.warning("Interest calc error: %s", e)

    # ── 3. Цена иска ─────────────────────────────────────────
    claim_price = principal + penalty + interest
    details_lines.append("3. Цена иска:")
    components = []
    if principal:
        components.append(f"основной долг {_fmt(principal)} руб.")
    if penalty:
        components.append(f"неустойка {_fmt(penalty)} руб.")
    if interest:
        components.append(f"проценты {_fmt(interest)} руб.")
    details_lines.append("   " + " + ".join(components) + f" = {_fmt(claim_price)} руб.")
    details_lines.append("")

    # ── 4. Госпошлина ─────────────────────────────────────────
    if is_property and claim_price > 0:
        if case_type == "arbitration":
            duty = calc_state_duty_arbitration(claim_price)
        else:
            duty = calc_state_duty_civil(claim_price)
    else:
        duty = calc_state_duty_non_property(case_type)

    # Доплата за моральный вред (отдельное неимущественное требование)
    moral_duty = 0.0
    if moral > 0:
        moral_duty = 300.0  # для физлица
        duty += moral_duty

    article = "333.21" if case_type == "arbitration" else "333.19"
    details_lines.append(f"4. Государственная пошлина (ст. {article} НК РФ):")
    if is_property and claim_price > 0:
        details_lines.append(f"   По имущественному требованию: {_fmt(duty - moral_duty)} руб.")
    else:
        details_lines.append(f"   По неимущественному требованию: {_fmt(duty - moral_duty)} руб.")
    if moral_duty > 0:
        details_lines.append(
            f"   По требованию о компенсации морального вреда: {_fmt(moral_duty)} руб."
        )
    details_lines.append(f"   Итого госпошлина: {_fmt(duty)} руб.")
    details_lines.append("")

    # ── 5. Итого ──────────────────────────────────────────────
    total = claim_price + moral + expenses + duty
    details_lines.append("5. Итого взыскиваемая сумма:")
    details_lines.append(
        f"   Цена иска: {_fmt(claim_price)} руб. + моральный вред: {_fmt(moral)} руб. "
        f"+ судебные расходы: {_fmt(expenses)} руб. + госпошлина: {_fmt(duty)} руб. "
        f"= {_fmt(total)} руб."
    )

    result = {
        "penalty_amount": penalty,
        "interest_amount": interest,
        "state_duty": duty,
        "total_claim": claim_price,
        "calculation_details": "\n".join(details_lines),
    }

    logger.info(
        "  Claim price=%.2f  duty=%.2f  total=%.2f",
        claim_price,
        duty,
        total,
    )
    return result


# ═══════════════════════════════════════════════════════════════
#  Госпошлина — суды общей юрисдикции (ст. 333.19 НК РФ)
# ═══════════════════════════════════════════════════════════════

def calc_state_duty_civil(claim: float) -> float:
    """Имущественный иск → суд общей юрисдикции."""
    claim = max(claim, 0)
    if claim <= 20_000:
        duty = claim * 0.04
        return max(duty, 400.0)
    elif claim <= 100_000:
        return 800 + (claim - 20_000) * 0.03
    elif claim <= 200_000:
        return 3_200 + (claim - 100_000) * 0.02
    elif claim <= 1_000_000:
        return 5_200 + (claim - 200_000) * 0.01
    else:
        duty = 13_200 + (claim - 1_000_000) * 0.005
        return min(duty, 60_000.0)


# ═══════════════════════════════════════════════════════════════
#  Госпошлина — арбитражные суды (ст. 333.21 НК РФ)
# ═══════════════════════════════════════════════════════════════

def calc_state_duty_arbitration(claim: float) -> float:
    """Имущественный иск → арбитражный суд."""
    claim = max(claim, 0)
    if claim <= 100_000:
        duty = claim * 0.04
        return max(duty, 2_000.0)
    elif claim <= 200_000:
        return 4_000 + (claim - 100_000) * 0.03
    elif claim <= 1_000_000:
        return 7_000 + (claim - 200_000) * 0.02
    elif claim <= 2_000_000:
        return 23_000 + (claim - 1_000_000) * 0.01
    else:
        duty = 33_000 + (claim - 2_000_000) * 0.005
        return min(duty, 200_000.0)


def calc_state_duty_non_property(case_type: str) -> float:
    """Неимущественный иск."""
    if case_type == "arbitration":
        return 6_000.0
    return 300.0  # физлицо — 300, юрлицо — 6000 (упрощение для прототипа)


# ═══════════════════════════════════════════════════════════════
#  Утилиты
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
    d1 = parse_date(start_str)
    d2 = parse_date(end_str)
    delta = (d2 - d1).days
    if delta < 0:
        raise ValueError(f"Начало ({start_str}) позже конца ({end_str})")
    return delta


def _to_float(value: Any) -> float:
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