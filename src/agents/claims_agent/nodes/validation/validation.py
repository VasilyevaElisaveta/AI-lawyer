"""
Модуль валидации полноты данных.
Поддерживает два режима: исковое заявление (lawsuit) и претензия (complaint).
"""
import os
import re
from typing import Any

from logger import LoggerFactory

from ..document_generation.calc import parse_date

from ...state import ClaimsAgentState

from ....utils import state_float, state_int


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

# Минимально необходимые текстовые поля (общие для иска и претензии)
_REQUIRED_ALWAYS: list[tuple[str, str]] = [
    ("plaintiff_info", "Не указана информация об отправителе/истце"),
    ("defendant_info", "Не указана информация об ответчике/получателе претензии"),
    ("facts", "Не указаны фактические обстоятельства дела"),
    ("claims", "Не указаны требования"),
]

# Дополнительные поля для имущественных споров
_REQUIRED_PROPERTY: list[tuple[str, str]] = [
    ("principal_amount", "Не указана сумма основного требования"),
]


def _is_property_dispute(state: ClaimsAgentState) -> bool:
    if state.get("is_property_dispute"):
        return True
    amount = state_float(state, "principal_amount", 0)
    if amount > 0:
        return True
    text = f"{state.get('claims', '')} {state.get('facts', '')}"
    return bool(re.search(r"\d+.*руб|сумм[аы]\s+\d", text, re.I))


def validation_node(state: ClaimsAgentState) -> dict[str, Any]:
    """Узел графа: проверка полноты данных."""
    doc_type = state.get("document_type", "lawsuit")
    logger.info("[claims][validation] проверка обязательных полей (документ=%s)", doc_type)
    errors: list[str] = []
    attempts: int = state_int(state, "validation_attempts", 0) + 1

    # ── Обязательные поля ─────────────────────────────────────
    for field, msg in _REQUIRED_ALWAYS:
        value = state.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(msg)

    is_property = _is_property_dispute(state)
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

    # ── Специфичная валидация для претензии ───────────────────
    if doc_type == "complaint":
        _validate_complaint_fields(state, errors)

    is_valid = len(errors) == 0
    if is_valid:
        logger.info("[claims][validation] успех (попытка %d)", attempts)
    else:
        logger.info(
            "[claims][validation] не хватает данных (попытка %d): %s",
            attempts,
            "; ".join(errors),
        )

    result: dict[str, Any] = {
        "validation_errors": errors,
        "is_valid": is_valid,
        "validation_attempts": attempts,
    }

    # Ожидание ввода пользователя: после исчерпания внутренних повторов intake
    if not is_valid:
        has_raw = bool(state.get("raw_input"))
        if not (has_raw and attempts < 2):
            result["current_agent"] = "claims_agent"

    return result


# ── Вспомогательные ───────────────────────────────────────────

def _validate_complaint_fields(state: ClaimsAgentState, errors: list[str]) -> None:
    """Дополнительная валидация для претензий."""
    response_deadline = state.get("complaint_response_deadline")
    if response_deadline is not None:
        if not isinstance(response_deadline, int) or response_deadline <= 0:
            errors.append(
                "Срок ответа на претензию должен быть положительным целым числом (дней)"
            )

    complaint_sphere = state.get("complaint_sphere", "")
    valid_spheres = {"consumer", "commercial", "labor", "other", ""}
    if complaint_sphere and complaint_sphere not in valid_spheres:
        errors.append(
            f"Неизвестная сфера претензии: '{complaint_sphere}'. "
            "Допустимые значения: consumer, commercial, labor, other"
        )

    complaint_type = state.get("complaint_type", "")
    valid_types = {"monetary", "non_monetary", ""}
    if complaint_type and complaint_type not in valid_types:
        errors.append(
            f"Неизвестный тип претензии: '{complaint_type}'. "
            "Допустимые значения: monetary, non_monetary"
        )


def _validate_date_pair(
    start: str, end: str, label: str, errors: list[str],
) -> None:
    """Если одна из дат пары заполнена, вторая тоже обязательна."""
    if start and not end:
        errors.append(f"Указана дата начала {label}, но не указана дата окончания")
    elif end and not start:
        errors.append(f"Указана дата окончания {label}, но не указана дата начала")
    if start and end:
        try:
            d_start = parse_date(start)
            d_end = parse_date(end)
            if d_start > d_end:
                errors.append(f"Дата начала {label} позже даты окончания")
        except ValueError:
            errors.append(f"Невозможно разобрать даты для расчёта {label}")
