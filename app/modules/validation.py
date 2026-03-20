"""
Модуль валидации полноты данных.
"""
from __future__ import annotations

from typing import Any

from app.core.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Минимально необходимые текстовые поля
_REQUIRED_ALWAYS: list[tuple[str, str]] = [
    ("plaintiff_info", "Не указана информация об истце"),
    ("defendant_info", "Не указана информация об ответчике"),
    ("facts", "Не указаны фактические обстоятельства дела"),
    ("claims", "Не указаны требования истца"),
]

# Дополнительные поля для имущественных споров
_REQUIRED_PROPERTY: list[tuple[str, str]] = [
    ("principal_amount", "Не указана сумма основного требования"),
]


def validation_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: проверка полноты данных."""
    logger.info("Validation node started")

    errors: list[str] = []
    attempts: int = state.get("validation_attempts", 0) + 1

    # ── Обязательные поля ─────────────────────────────────────
    for field, msg in _REQUIRED_ALWAYS:
        value = state.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(msg)

    # ── Имущественный спор ────────────────────────────────────
    is_property = state.get("is_property_dispute", False)
    if is_property:
        for field, msg in _REQUIRED_PROPERTY:
            value = state.get(field)
            if not value or (isinstance(value, (int, float)) and value <= 0):
                errors.append(msg)

    # ── Проверка корректности сумм ────────────────────────────
    for amount_field in (
        "principal_amount",
        "penalty_amount",
        "interest_amount",
        "moral_damage",
        "court_expenses",
    ):
        val = state.get(amount_field, 0)
        if isinstance(val, (int, float)) and val < 0:
            errors.append(f"Отрицательная сумма в поле {amount_field}")

    # ── Проверка дат ──────────────────────────────────────────
    _validate_date_pair(
        state.get("penalty_start_date", ""),
        state.get("penalty_end_date", ""),
        "неустойки",
        errors,
    )
    _validate_date_pair(
        state.get("interest_start_date", ""),
        state.get("interest_end_date", ""),
        "процентов по ст. 395",
        errors,
    )

    is_valid = len(errors) == 0
    logger.info(
        "  Validation attempt %d: %s  (errors: %d)",
        attempts,
        "PASSED" if is_valid else "FAILED",
        len(errors),
    )
    if errors:
        for e in errors:
            logger.info("    • %s", e)

    return {
        "validation_errors": errors,
        "is_valid": is_valid,
        "validation_attempts": attempts,
    }


# ── Вспомогательные ───────────────────────────────────────────

def _validate_date_pair(
    start: str, end: str, label: str, errors: list[str],
) -> None:
    """Если одна из дат пары заполнена, вторая тоже обязательна."""
    if start and not end:
        errors.append(f"Указана дата начала {label}, но не указана дата окончания")
    elif end and not start:
        errors.append(f"Указана дата окончания {label}, но не указана дата начала")
    if start and end:
        from app.modules.calculator_ import parse_date
        try:
            d_start = parse_date(start)
            d_end = parse_date(end)
            if d_start > d_end:
                errors.append(f"Дата начала {label} позже даты окончания")
        except ValueError:
            errors.append(f"Невозможно разобрать даты для расчёта {label}")