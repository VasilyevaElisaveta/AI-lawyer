import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm_client import GigaChatClient
from ..state import AgentState
from ..prompts import (
    CLASSIFICATION_PROMPT,
    CLASSIFICATION_SYSTEM,
    CONTRACT_INTAKE_HUMAN,
    CONTRACT_INTAKE_SYSTEM,
)
from ..fields import (
    _CONTRACT_FIELDS,
)

from ...utils import safe_parse_json, render_template


def _map_structured(data: Dict, field_map: Dict[str, str]) -> Dict[str, Any]:
    """Маппинг полей из input_data в state по заданной карте полей."""
    updates: dict[str, Any] = {}
    for src, dst in field_map.items():
        if src in data and data[src] is not None:
            updates[dst] = data[src]
    return updates


async def _classify_request(text: str, state: AgentState, llm: GigaChatClient) -> Dict[str, Any]:
    """Классификация запроса: case_type, case_category."""
    existing_state = json.dumps({k: v for k, v in state.items() if k in ["case_type", "case_category"]}, ensure_ascii=False)
    prompt = CLASSIFICATION_PROMPT.format(
        existing_state=existing_state,
        user_message=text,
    )

    try:
        content = await llm.ainvoke([
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
        content = await llm.ainvoke([
            SystemMessage(content=CONTRACT_INTAKE_SYSTEM),
            HumanMessage(content=prompt_text),
        ])
        data = safe_parse_json(content)
        return _map_structured(data, _CONTRACT_FIELDS)

    except Exception as e:
        # Фолбэк: кладём весь текст в contract_subject
        return {"contract_subject": text}


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