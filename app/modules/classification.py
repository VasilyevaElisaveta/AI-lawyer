"""
Модуль классификации дела:
  • тип судопроизводства (civil / arbitration)
  • категория спора
  • является ли спор имущественным
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.state import AgentState
from app.services.llm_client import invoke_llm
from app.utils.logger import get_logger
from app.utils.prompts import (
    CLASSIFICATION_HUMAN,
    CLASSIFICATION_SYSTEM,
    render_template,
)

logger = get_logger(__name__)

_VALID_CASE_TYPES = {"civil", "arbitration"}
_VALID_CATEGORIES = {
    "debt_collection",
    "employment",
    "consumer",
    "property",
    "family",
    "housing",
    "contract",
    "tort",
    "other",
}


def classification_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: классификация дела."""
    logger.info("Classification node started")

    # Идемпотентность: если уже классифицировано — пропускаем
    if state.get("case_type") and state.get("case_category"):
        logger.info("  Already classified — skipping")
        return {}

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
        data = _parse_classification(content)
        logger.info(
            "  Classified: type=%s  category=%s  property=%s",
            data["case_type"],
            data["case_category"],
            data["is_property_dispute"],
        )
        return data

    except Exception as e:
        logger.error("Classification failed: %s — using defaults", e)
        return {
            "case_type": "civil",
            "case_category": "other",
            "is_property_dispute": True,
        }


def _parse_classification(text: str) -> dict[str, Any]:
    import re

    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    raw = m.group(1) if m else text[text.find("{") : text.rfind("}") + 1]
    data = json.loads(raw)

    case_type = data.get("case_type", "civil")
    if case_type not in _VALID_CASE_TYPES:
        case_type = "civil"

    category = data.get("case_category", "other")
    if category not in _VALID_CATEGORIES:
        category = "other"

    return {
        "case_type": case_type,
        "case_category": category,
        "is_property_dispute": bool(data.get("is_property_dispute", True)),
    }