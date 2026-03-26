"""
Модуль валидации полноты данных.
Чистый Python — без вызовов LLM.

Поддерживает два типа документов:
  • lawsuit        — исковое заявление
  • pretrial_claim — досудебная претензия
"""
from __future__ import annotations

import re
from typing import Any

from app.core.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Правила проверки по типам документов
# ═══════════════════════════════════════════════════════════════

# Минимально необходимые текстовые поля для иска
_REQUIRED_LAWSUIT: list[tuple[str, str]] = [
    ("plaintiff_info", "Не указана информация об истце"),
    ("defendant_info", "Не указана информация об ответчике"),
    ("facts", "Не указаны фактические обстоятельства дела"),
    ("claims", "Не указаны требования истца"),
]

# Дополнительные поля для имущественных исков
_REQUIRED_LAWSUIT_PROPERTY: list[tuple[str, str]] = [
    ("principal_amount", "Не указана сумма основного требования"),
]

# Минимально необходимые поля для претензии
_REQUIRED_PRETRIAL: list[tuple[str, str]] = [
    ("sender_info", "Не указана информация об отправителе претензии"),
    ("recipient_info", "Не указана информация о получателе претензии"),
    ("facts", "Не указаны фактические обстоятельства"),
    ("sender_demands", "Не указаны требования отправителя"),
]


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def validation_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: проверка полноты данных."""
    logger.info("▶ Validation node started")

    errors: list[str] = []
    warnings: list[str] = []
    attempts: int = state.get("validation_attempts", 0) + 1
    doc_type = state.get("doc_type", "lawsuit")

    # ── Проверки по типу документа ────────────────────────────
    if doc_type == "pretrial_claim":
        _validate_pretrial(state, errors, warnings)
    else:
        _validate_lawsuit(state, errors, warnings)

    # ── Общие проверки (для обоих типов) ──────────────────────

    # Отрицательные суммы
    for amount_field in (
        "principal_amount",
        "penalty_amount",
        "interest_amount",
        "loan_interest_amount",
        "moral_damage",
        "court_expenses",
    ):
        val = state.get(amount_field, 0)
        if isinstance(val, (int, float)) and val < 0:
            errors.append(f"Отрицательная сумма в поле {amount_field}")

    # Общие пары дат
    _validate_date_pair(
        state.get("penalty_start_date", ""),
        state.get("penalty_end_date", ""),
        "неустойки",
        errors,
    )
    _validate_date_pair(
        state.get("loan_start_date", ""),
        state.get("loan_end_date", ""),
        "процентов за пользование",
        errors,
    )

    # ── Результат ─────────────────────────────────────────────
    is_valid = len(errors) == 0

    logger.info(
        "  Validation attempt %d [%s]: %s  (errors: %d, warnings: %d)",
        attempts,
        doc_type,
        "PASSED" if is_valid else "FAILED",
        len(errors),
        len(warnings),
    )
    for e in errors:
        logger.info("    ✗ %s", e)
    for w in warnings:
        logger.info("    ⚠ %s", w)

    return {
        "validation_errors": errors,
        "validation_warnings": warnings,
        "is_valid": is_valid,
        "validation_attempts": attempts,
    }


# ═══════════════════════════════════════════════════════════════
#  Проверки для искового заявления
# ═══════════════════════════════════════════════════════════════

def _validate_lawsuit(state: AgentState, errors: list[str], warnings: list[str]) -> None:
    """Проверки, специфичные для исков."""

    # Обязательные поля
    for field, msg in _REQUIRED_LAWSUIT:
        value = state.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(msg)

    # Имущественный спор — сумма обязательна
    is_property = state.get("is_property_dispute", False)
    if is_property:
        for field, msg in _REQUIRED_LAWSUIT_PROPERTY:
            value = state.get(field)
            if not value or (isinstance(value, (int, float)) and value <= 0):
                errors.append(msg)

    # Даты процентов по ст. 395
    _validate_date_pair(
        state.get("interest_start_date", ""),
        state.get("interest_end_date", ""),
        "процентов по ст. 395",
        errors,
    )

    # Идентификаторы истца
    plaintiff_info = state.get("plaintiff_info", "")
    if plaintiff_info and not _has_identifier(plaintiff_info):
        warnings.append(
            "В данных истца не найден идентификатор (ИНН, СНИЛС или паспортные данные). "
            "По ст. 131 ГПК РФ рекомендуется указать хотя бы один идентификатор."
        )

    # Идентификаторы ответчика
    defendant_info = state.get("defendant_info", "")
    if defendant_info and not _has_identifier(defendant_info):
        warnings.append(
            "В данных ответчика не найден идентификатор (ИНН, ОГРН, СНИЛС, паспорт). "
            "Если известен — рекомендуется указать."
        )


# ═══════════════════════════════════════════════════════════════
#  Проверки для досудебной претензии
# ═══════════════════════════════════════════════════════════════

def _validate_pretrial(state: AgentState, errors: list[str], warnings: list[str]) -> None:
    """Проверки, специфичные для претензий."""

    # Обязательные поля
    for field, msg in _REQUIRED_PRETRIAL:
        value = state.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(msg)

    # Имущественный спор — сумма обязательна
    is_property = state.get("is_property_dispute", False)
    if is_property:
        principal = state.get("principal_amount", 0)
        if not principal or (isinstance(principal, (int, float)) and principal <= 0):
            errors.append("Не указана сумма основного требования")

    # Срок ответа — рекомендация
    deadline = state.get("response_deadline", "")
    if not deadline:
        warnings.append(
            "Не указан срок для добровольного удовлетворения. "
            "Будет установлен 10 календарных дней по умолчанию."
        )

    # Основание — рекомендация
    basis = state.get("basis", "")
    if not basis:
        warnings.append("Не указано основание претензии (номер/дата договора).")

    # Идентификаторы отправителя
    sender_info = state.get("sender_info", "")
    if sender_info and not _has_identifier(sender_info):
        warnings.append(
            "В данных отправителя не найден идентификатор (ИНН, ОГРН, паспорт)."
        )


# ═══════════════════════════════════════════════════════════════
#  Вспомогательные функции
# ═══════════════════════════════════════════════════════════════

def _validate_date_pair(
    start: str, end: str, label: str, errors: list[str],
) -> None:
    """Если одна из дат пары заполнена, вторая тоже обязательна."""
    if start and not end:
        errors.append(f"Указана дата начала {label}, но не указана дата окончания")
    elif end and not start:
        errors.append(f"Указана дата окончания {label}, но не указана дата начала")
    if start and end:
        from app.modules.calculator import parse_date
        try:
            d_start = parse_date(start)
            d_end = parse_date(end)
            if d_start > d_end:
                errors.append(f"Дата начала {label} позже даты окончания")
        except ValueError:
            errors.append(f"Невозможно разобрать даты для расчёта {label}")


def _has_identifier(info: str) -> bool:
    """Проверяет наличие хотя бы одного идентификатора в строке."""
    info_upper = info.upper()

    # ИНН: 10 или 12 цифр
    if re.search(r"ИНН\s*[:\-]?\s*\d{10,12}", info_upper):
        return True

    # ОГРН / ОГРНИП
    if re.search(r"ОГРН(?:ИП)?\s*[:\-]?\s*\d{13,15}", info_upper):
        return True

    # СНИЛС: ХХХ-ХХХ-ХХХ ХХ
    if re.search(r"СНИЛС|(\d{3}[\-\s]?\d{3}[\-\s]?\d{3}[\-\s]?\d{2})", info_upper):
        return True

    # Паспорт: серия ХХХХ номер ХХХХХХ
    if re.search(r"ПАСПОРТ|СЕРИЯ\s*\d{4}", info_upper):
        return True

    return False