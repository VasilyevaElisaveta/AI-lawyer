from __future__ import annotations

import json
import re
from typing import Any

from .fields import BOOLEAN_FIELDS, FIELD_LABELS, NUMERIC_FIELDS, REQUIRED_FIELDS_BY_TYPE
from .state import AgentState
from .utils import parse_json


def normalize_field_value(key: str, value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
    if key in BOOLEAN_FIELDS:
        if isinstance(value, str):
            lowered = value.lower()
            return lowered in ["да", "есть", "true", "да, прошу", "прошу"]
        return bool(value)
    if key in NUMERIC_FIELDS and isinstance(value, str):
        digits = re.sub(r"[^0-9,\.\-]", "", value)
        if digits:
            try:
                if "." in digits or "," in digits:
                    return float(digits.replace(",", "."))
                return int(digits)
            except ValueError:
                return value
    return value


def merge_fields(state: AgentState, fields: dict[str, Any]) -> None:
    for key, value in fields.items():
        if value is None:
            continue
        value = normalize_field_value(key, value)
        if value == "":
            continue
        state.set(key, value)


def safe_parse_json(text: str) -> dict[str, Any]:
    try:
        return parse_json(text)
    except Exception:
        simple_match = re.search(r"\{.*\}", text, re.DOTALL)
        if simple_match:
            try:
                return json.loads(simple_match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}


def find_missing_required_fields(state: AgentState) -> list[str]:
    doc_type = state.get("doc_type", "lawsuit")
    required = REQUIRED_FIELDS_BY_TYPE.get(doc_type, [])
    missing: list[str] = []
    for key in required:
        value = state.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)
    return missing


def build_missing_fields_prompt(missing_fields: list[str]) -> str:
    lines = [
        "Для продолжения подготовки документа нужны дополнительные данные:",
    ]
    for key in missing_fields:
        lines.append(f"- {FIELD_LABELS.get(key, key)}")
    lines.append(
        "Пожалуйста, пришлите недостающие сведения. Если хотите, можете отвечать простым текстом без формальностей."
    )
    return "\n".join(lines)
