"""
Модуль сбора фактов (Intake).
• Если передан input_data (dict) — маппинг полей напрямую.
• Если передан raw_input (свободный текст) — извлечение через LLM.
"""
import os
import json
import re
from typing import Any

from libs.logger import LoggerFactory

from langchain_core.messages import HumanMessage, SystemMessage

from claims_agent.state import ClaimsAgentState
from claims_agent.services.llm_client import invoke_llm
from claims_agent.prompts import (
    INTAKE_HUMAN,
    INTAKE_SYSTEM,
    render_template,
)


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") is not "DEBUG" else None,
)

# Поля, которые маппятся 1-к-1 из input_data в state
_FIELD_MAP: dict[str, str] = {
    "document_type": "document_type",
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
    # Специфичные для претензии поля
    "complaint_type": "complaint_type",
    "complaint_sphere": "complaint_sphere",
    "complaint_sending_method": "complaint_sending_method",
    "complaint_response_deadline": "complaint_response_deadline",
    "complaint_deadline_basis": "complaint_deadline_basis",
}


def intake_node(state: ClaimsAgentState) -> dict[str, Any]:
    """Узел графа: сбор и структурирование входных данных."""
    logger.info("Intake node started")

    # 1. Структурированный ввод — приоритет
    input_data: dict | None = state.get("input_data")
    if input_data:
        logger.info("  Structured input detected — mapping fields")
        return _map_structured(input_data)

    # 2. Свободный текст → LLM-извлечение
    raw_input: str = state.get("raw_input", "")
    if not raw_input:
        logger.warning("  No input provided")
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}

    logger.info("  Raw text detected — extracting via LLM")
    return _extract_from_text(raw_input, state)


# ── Вспомогательные функции ───────────────────────────────────

def _map_structured(data: dict) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for src, dst in _FIELD_MAP.items():
        if src in data and data[src] is not None:
            updates[dst] = data[src]
    return updates


def _extract_from_text(text: str, state: ClaimsAgentState) -> dict[str, Any]:
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
        INTAKE_HUMAN,
        {"user_input": text, "additional_context": additional},
    )

    try:
        content = invoke_llm([
            SystemMessage(content=INTAKE_SYSTEM),
            HumanMessage(content=prompt_text),
        ])
        data = _parse_json(content)
        return _map_structured(data)

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
