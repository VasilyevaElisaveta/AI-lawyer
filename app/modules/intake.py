"""
Модуль сбора фактов (Intake).

Поддерживает два режима ввода:
  • Структурированный (input_data dict) — прямой маппинг полей
  • Свободный текст (raw_input str) — извлечение через LLM

Поддерживает два типа документов:
  • lawsuit        — исковое заявление
  • pretrial_claim — досудебная претензия
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.state import AgentState
from app.services.llm_client import invoke_llm
from app.utils.logger import get_logger
from app.utils.prompts import (
    INTAKE_HUMAN,
    INTAKE_SYSTEM,
    PRETRIAL_INTAKE_HUMAN,
    PRETRIAL_INTAKE_SYSTEM,
    render_template,
)

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Маппинг полей для каждого типа документа
# ═══════════════════════════════════════════════════════════════

# Поля для искового заявления
_LAWSUIT_FIELDS: dict[str, str] = {
    "plaintiff_info": "plaintiff_info",
    "defendant_info": "defendant_info",
    "third_parties_info": "third_parties_info",
    "court_info": "court_info",
    "facts": "facts",
    "documents": "documents",
    "claims": "claims",
    "pretrial_settlement": "pretrial_settlement",
    "principal_amount": "principal_amount",
    "penalty_amount": "penalty_amount",
    "interest_amount": "interest_amount",
    "moral_damage": "moral_damage",
    "court_expenses": "court_expenses",
    "penalty_rate": "penalty_rate",
    "penalty_start_date": "penalty_start_date",
    "penalty_end_date": "penalty_end_date",
    "interest_start_date": "interest_start_date",
    "interest_end_date": "interest_end_date",
    "cbr_key_rate": "cbr_key_rate",
    "loan_interest_rate": "loan_interest_rate",
    "loan_start_date": "loan_start_date",
    "loan_end_date": "loan_end_date",
    "request_ongoing_penalty": "request_ongoing_penalty",
    "request_ongoing_interest": "request_ongoing_interest",
}

# Поля для досудебной претензии
_PRETRIAL_FIELDS: dict[str, str] = {
    "sender_info": "sender_info",
    "recipient_info": "recipient_info",
    "claim_type": "claim_type",
    "basis": "basis",
    "facts": "facts",
    "supporting_documents": "supporting_documents",
    "sender_demands": "sender_demands",
    "response_deadline": "response_deadline",
    "principal_amount": "principal_amount",
    "penalty_amount": "penalty_amount",
    "interest_amount": "interest_amount",
    "moral_damage": "moral_damage",
    "penalty_rate": "penalty_rate",
    "penalty_start_date": "penalty_start_date",
    "penalty_end_date": "penalty_end_date",
    "loan_interest_rate": "loan_interest_rate",
    "loan_start_date": "loan_start_date",
    "loan_end_date": "loan_end_date",
}


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def intake_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: сбор и структурирование входных данных."""
    logger.info("▶ Intake node started")

    doc_type = state.get("doc_type", "lawsuit")

    # 1. Структурированный ввод — приоритет
    input_data: dict | None = state.get("input_data")
    if input_data:
        logger.info("  Structured input detected — mapping fields (doc_type=%s)", doc_type)
        field_map = _PRETRIAL_FIELDS if doc_type == "pretrial_claim" else _LAWSUIT_FIELDS
        return _map_structured(input_data, field_map)

    # 2. Свободный текст → LLM-извлечение
    raw_input: str = state.get("raw_input", "")
    if not raw_input:
        logger.warning("  No input provided")
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}

    logger.info("  Raw text detected — extracting via LLM (doc_type=%s)", doc_type)
    return _extract_from_text(raw_input, state, doc_type)


# ═══════════════════════════════════════════════════════════════
#  Вспомогательные функции
# ═══════════════════════════════════════════════════════════════

def _map_structured(data: dict, field_map: dict[str, str]) -> dict[str, Any]:
    """Маппинг полей из input_data в state по заданной карте полей."""
    updates: dict[str, Any] = {}
    for src, dst in field_map.items():
        if src in data and data[src] is not None:
            updates[dst] = data[src]
    return updates


def _extract_from_text(text: str, state: AgentState, doc_type: str) -> dict[str, Any]:
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

    # Выбираем промпт по типу документа
    if doc_type == "pretrial_claim":
        system = PRETRIAL_INTAKE_SYSTEM
        human_template = PRETRIAL_INTAKE_HUMAN
        field_map = _PRETRIAL_FIELDS
    else:
        system = INTAKE_SYSTEM
        human_template = INTAKE_HUMAN
        field_map = _LAWSUIT_FIELDS

    prompt_text = render_template(
        human_template,
        {"user_input": text, "additional_context": additional},
    )

    try:
        content = invoke_llm([
            SystemMessage(content=system),
            HumanMessage(content=prompt_text),
        ])
        data = _parse_json(content)
        return _map_structured(data, field_map)

    except Exception as e:
        logger.error("Intake LLM extraction failed: %s", e)
        # Фолбэк: кладём весь текст в facts
        return {"facts": text}


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