"""
Модуль правового исследования.
Прототип: генерация применимых норм через LLM.
Будущее: RAG по векторной БД с кодексами и законами.
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
    RESEARCH_HUMAN,
    RESEARCH_SYSTEM,
    render_template,
)

logger = get_logger(__name__)

_CASE_TYPE_LABELS = {
    "civil": "Гражданское судопроизводство (суд общей юрисдикции)",
    "arbitration": "Арбитражное судопроизводство",
}


def research_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: определение применимых норм права."""
    logger.info("Research node started")

    case_type = state.get("case_type", "civil")

    prompt = render_template(
        RESEARCH_HUMAN,
        {
            "case_type_label": _CASE_TYPE_LABELS.get(case_type, case_type),
            "case_category": state.get("case_category", "other"),
            "is_property_dispute": state.get("is_property_dispute", False),
            "facts": state.get("facts", ""),
            "claims": state.get("claims", ""),
        },
    )

    try:
        content = invoke_llm([
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=prompt),
        ])
        data = _parse_research(content)
        logger.info("  Research completed, laws length: %d chars", len(data.get("applicable_laws", "")))
        return data

    except Exception as e:
        logger.error("Research failed: %s", e)
        return {
            "applicable_laws": "[Не удалось определить применимые нормы — требуется ручная проверка]",
            "legal_positions": "",
        }


def _parse_research(text: str) -> dict[str, Any]:
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            raw = text[start : end + 1]
        else:
            # Если JSON не найден — воспринимаем весь текст как applicable_laws
            return {"applicable_laws": text.strip(), "legal_positions": ""}

    data = json.loads(raw)
    return {
        "applicable_laws": data.get("applicable_laws", ""),
        "legal_positions": data.get("legal_positions", ""),
    }


# ═══════════════════════════════════════════════════════════════
#  Заготовка для RAG (будет подключена позднее)
# ═══════════════════════════════════════════════════════════════

def _rag_search(query: str, top_k: int = 5) -> list[str]:
    """
    TODO: Поиск по векторной БД с кодексами/законами.
    Будет вызываться из research_node вместо/дополнительно к LLM.
    """
    # from app.services.vector_db import get_retriever
    # retriever = get_retriever()
    # docs = retriever.invoke(query)
    # return [d.page_content for d in docs[:top_k]]
    return []