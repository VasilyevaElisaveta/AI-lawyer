"""Разбор структурированного текста пользователя без LLM (Истец: ..., Сумма: ...)."""
from __future__ import annotations
import re
from typing import Any

_FIELD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("plaintiff_info", re.compile(r"(?:истец|заявитель|отправитель)\s*[:：]\s*([^,\n;]+)", re.I)),
    ("defendant_info", re.compile(r"(?:ответчик|получатель)\s*[:：]\s*([^,\n;]+)", re.I)),
    ("claims", re.compile(r"(?:требовани[яе]|просител?ь?ство)\s*[:：]\s*([^,\n;]+)", re.I)),
    ("facts", re.compile(r"(?:обстоятельства|факты)\s*[:：]\s*([^,\n;]+)", re.I)),
    (
        "principal_amount",
        re.compile(
            r"(?:сумма\s+основного\s+требования|сумма\s+иска|сумма)\s*[:：]\s*"
            r"(\d[\d\s]*(?:[.,]\d+)?)\s*(?:руб(?:лей|\.?)?)?",
            re.I,
        ),
    ),
]


def _parse_amount(raw: str) -> float | None:
    cleaned = re.sub(r"\s+", "", raw).replace(",", ".")
    try:
        value = float(cleaned)
        return value if value > 0 else None
    except ValueError:
        return None


def parse_labeled_user_text(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        return {}
    result: dict[str, Any] = {}
    for field, pattern in _FIELD_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(1).strip()
        if field == "principal_amount":
            amount = _parse_amount(value)
            if amount is not None:
                result[field] = amount
        elif value:
            result[field] = value
    if not result.get("facts") and len(text) > 20 and not result:
        return {}
    return result
