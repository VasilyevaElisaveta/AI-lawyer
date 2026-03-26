"""
Модуль классификации дела.

Для исков определяет:
  • тип судопроизводства (civil / arbitration)
  • категорию спора
  • является ли спор имущественным

Для претензий определяет:
  • категорию спора
  • является ли спор имущественным
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
    CLASSIFICATION_HUMAN,
    CLASSIFICATION_SYSTEM,
    PRETRIAL_CLASSIFICATION_HUMAN,
    PRETRIAL_CLASSIFICATION_SYSTEM,
    render_template,
)

logger = get_logger(__name__)

_VALID_CASE_TYPES = {"civil", "arbitration"}
_VALID_CATEGORIES = {
    "debt_collection", "debt", "employment", "consumer",
    "property", "family", "housing", "contract", "tort",
    "insurance", "other",
}


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def classification_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: классификация дела."""
    logger.info("▶ Classification node started")

    # Идемпотентность: если уже классифицировано — пропускаем
    if state.get("case_type") and state.get("case_category"):
        logger.info("  Already classified — skipping")
        return {}

    doc_type = state.get("doc_type", "lawsuit")

    if doc_type == "pretrial_claim":
        return _classify_pretrial(state)
    else:
        return _classify_lawsuit(state)


# ═══════════════════════════════════════════════════════════════
#  Классификация исков
# ═══════════════════════════════════════════════════════════════

def _classify_lawsuit(state: AgentState) -> dict[str, Any]:
    """Классификация для искового заявления."""
    prompt = render_template(
        CLASSIFICATION_HUMAN,
        {
            "plaintiff_info": state.get("plaintiff_info", ""),
            "defendant_info": state.get("defendant_info", ""),
            "facts": state.get("facts", ""),
            "claims": state.get("claims", ""),
        },
    )

    try:
        content = invoke_llm([
            SystemMessage(content=CLASSIFICATION_SYSTEM),
            HumanMessage(content=prompt),
        ])
        data = _extract_json(content)

        case_type = data.get("case_type", "civil")
        if case_type not in _VALID_CASE_TYPES:
            case_type = "civil"

        category = data.get("case_category", "other")
        if category not in _VALID_CATEGORIES:
            category = "other"

        result = {
            "case_type": case_type,
            "case_category": category,
            "is_property_dispute": bool(data.get("is_property_dispute", True)),
        }

        logger.info(
            "  Classified [lawsuit]: type=%s  category=%s  property=%s",
            result["case_type"],
            result["case_category"],
            result["is_property_dispute"],
        )
        return result

    except Exception as e:
        logger.error("Classification failed: %s — using defaults", e)
        return {
            "case_type": "civil",
            "case_category": "other",
            "is_property_dispute": True,
        }


# ═══════════════════════════════════════════════════════════════
#  Классификация претензий
# ═══════════════════════════════════════════════════════════════

def _classify_pretrial(state: AgentState) -> dict[str, Any]:
    """Классификация для досудебной претензии."""
    prompt = render_template(
        PRETRIAL_CLASSIFICATION_HUMAN,
        {
            "sender_info": state.get("sender_info", ""),
            "recipient_info": state.get("recipient_info", ""),
            "facts": state.get("facts", ""),
            "sender_demands": state.get("sender_demands", ""),
        },
    )

    try:
        content = invoke_llm([
            SystemMessage(content=PRETRIAL_CLASSIFICATION_SYSTEM),
            HumanMessage(content=prompt),
        ])
        data = _extract_json(content)

        category = data.get("case_category", "other")
        if category not in _VALID_CATEGORIES:
            category = "other"

        result = {
            "case_category": category,
            "is_property_dispute": bool(data.get("is_property_dispute", True)),
        }

        logger.info(
            "  Classified [pretrial]: category=%s  property=%s",
            result["case_category"],
            result["is_property_dispute"],
        )
        return result

    except Exception as e:
        logger.error("Pretrial classification failed: %s — using defaults", e)
        return {
            "case_category": "other",
            "is_property_dispute": True,
        }


# ═══════════════════════════════════════════════════════════════
#  Утилита парсинга JSON
# ═══════════════════════════════════════════════════════════════

def _extract_json(text: str) -> dict:
    """Извлекает JSON из ответа LLM (может быть обёрнут в markdown)."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    raw = m.group(1) if m else text[text.find("{") : text.rfind("}") + 1]
    return json.loads(raw)