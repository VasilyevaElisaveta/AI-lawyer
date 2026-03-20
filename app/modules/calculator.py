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
    pass

# ═══════════════════════════════════════════════════════════════
#  Госпошлина — суды общей юрисдикции
# ═══════════════════════════════════════════════════════════════


def calc_state_duty_civil(claim: float) -> float:
    pass


# ═══════════════════════════════════════════════════════════════
#  Госпошлина — арбитражные суды
# ═══════════════════════════════════════════════════════════════

def calc_state_duty_arbitration(claim: float) -> float:
    pass


def calc_state_duty_non_property(case_type: str) -> float:
    pass


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