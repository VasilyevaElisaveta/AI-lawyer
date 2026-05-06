"""
Модуль валидации полноты данных.
Поддерживает два режима: исковое заявление (lawsuit) и претензия (complaint).
"""
import os
from typing import Any

from libs.logger import LoggerFactory

from claims_agent.state import ClaimsAgentState


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") is not "DEBUG" else None,
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


def validation_node(state: ClaimsAgentState) -> dict[str, Any]:
    """Узел графа: проверка полноты данных."""
    logger.info("Validation node started")

    document_type = state.get("document_type", "lawsuit")
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

    # ── Специфичная валидация для претензии ───────────────────
    if document_type == "complaint":
        _validate_complaint_fields(state, errors)

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
        from claims_agent.nodes.document_generation.calc import parse_date
        try:
            d_start = parse_date(start)
            d_end = parse_date(end)
            if d_start > d_end:
                errors.append(f"Дата начала {label} позже даты окончания")
        except ValueError:
            errors.append(f"Невозможно разобрать даты для расчёта {label}")
