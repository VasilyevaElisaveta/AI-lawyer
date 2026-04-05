from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .fields import (
    _CONTRACT_FIELDS,
    BOOLEAN_FIELDS,
    FIELD_LABELS,
    NUMERIC_FIELDS,
    REQUIRED_FIELDS_BY_TYPE,
)
from .llm_client import GigaChatClient
from .prompts import (
    CLASSIFICATION_PROMPT,
    CLASSIFICATION_SYSTEM,
    CONTRACT_INTAKE_HUMAN,
    CONTRACT_INTAKE_SYSTEM,
)
from .state import AgentState
from .utils import render_template


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


def _parse_json(text: str) -> dict:
    """Извлекает JSON из ответа LLM (может быть обёрнут в markdown)."""
    # Пробуем ```json ... ```
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Пробуем найти { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"JSON not found in LLM response (first 300 chars): {text[:300]}")


def merge_fields(state: AgentState, fields: dict[str, Any]) -> None:
    for key, value in fields.items():
        if value is None:
            continue
        value = normalize_field_value(key, value)
        if value == "":
            continue
        state[key] = value


def safe_parse_json(text: str) -> dict[str, Any]:
    try:
        return _parse_json(text)
    except Exception:
        simple_match = re.search(r"\{.*\}", text, re.DOTALL)
        if simple_match:
            try:
                return json.loads(simple_match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}


def find_missing_required_fields(state: AgentState) -> list[str]:
    required = REQUIRED_FIELDS_BY_TYPE.get("contract", [])
    missing: list[str] = []
    for key in required:
        value = state.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)
    return missing


# ═══════════════════════════════════════════════════════════════
#  Intake node functions
# ═══════════════════════════════════════════════════════════════

async def intake_node(state: AgentState, llm: GigaChatClient) -> dict[str, Any]:
    """Узел графа: сбор и структурирование входных данных."""
    # 1. Структурированный ввод — приоритет
    input_data: dict | None = state.get("input_data")
    if input_data:
        updates = _map_structured(input_data, _CONTRACT_FIELDS)
        # Классификация из input_data, если есть
        if "case_type" in input_data:
            updates["case_type"] = input_data["case_type"]
        if "case_category" in input_data:
            updates["case_category"] = input_data["case_category"]
        return updates

    # 2. Свободный текст → классификация + извлечение
    raw_input: str = state.get("raw_input", "")
    if not raw_input:
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}

    # Сначала классификация
    classification_updates = await _classify_request(raw_input, state, llm)
    # Затем извлечение
    extraction_updates = await _extract_from_text(raw_input, state, llm)
    # Объединяем
    updates = {**classification_updates, **extraction_updates}
    # Устанавливаем doc_type на основе case_category
    if updates.get("case_category") == "contract":
        updates["doc_type"] = "contract"
    state.update(updates)
    return dict(state)


def _map_structured(data: dict, field_map: dict[str, str]) -> dict[str, Any]:
    """Маппинг полей из input_data в state по заданной карте полей."""
    updates: dict[str, Any] = {}
    for src, dst in field_map.items():
        if src in data and data[src] is not None:
            updates[dst] = data[src]
    return updates


async def _classify_request(text: str, state: AgentState, llm: GigaChatClient) -> dict[str, Any]:
    """Классификация запроса: case_type, case_category."""
    existing_state = json.dumps({k: v for k, v in state.items() if k in ["case_type", "case_category"]}, ensure_ascii=False)
    prompt = CLASSIFICATION_PROMPT.format(
        existing_state=existing_state,
        user_message=text,
    )

    try:
        content = await llm.invoke([
            SystemMessage(content=CLASSIFICATION_SYSTEM),
            HumanMessage(content=prompt),
        ])
        parsed = safe_parse_json(content)
    except Exception:
        parsed = {}

    updates = {}
    if "case_type" in parsed:
        updates["case_type"] = parsed["case_type"]
    if "case_category" in parsed:
        updates["case_category"] = parsed["case_category"]
    return updates


async def _extract_from_text(text: str, state: AgentState, llm: GigaChatClient) -> dict[str, Any]:
    """Извлечение структурированных данных из свободного текста через LLM."""
    # Если это повторная попытка — добавляем контекст ошибок
    validation_errors = state.get("validation_errors", [])
    additional = ""
    if validation_errors:
        additional = (
            "\n\nПри предыдущей проверке обнаружены недостающие данные:\n"
            + "\n".join(f"- {e}" for e in validation_errors)
            + "\n\nПостарайся найти или вывести эту информацию из текста."
        )

    prompt_text = render_template(
        CONTRACT_INTAKE_HUMAN,
        {"user_input": text, "additional_context": additional},
    )

    try:
        content = await llm.invoke([
            SystemMessage(content=CONTRACT_INTAKE_SYSTEM),
            HumanMessage(content=prompt_text),
        ])
        data = _parse_json(content)
        return _map_structured(data, _CONTRACT_FIELDS)

    except Exception as e:
        # Фолбэк: кладём весь текст в contract_subject
        return {"contract_subject": text}
