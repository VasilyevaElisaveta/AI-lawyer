"""
Модуль генерации искового заявления.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.state import AgentState
from app.services.llm_client import invoke_llm
from app.utils.logger import get_logger
from app.utils.prompts import (
    GENERATOR_HUMAN,
    GENERATOR_REWORK_HUMAN,
    GENERATOR_SYSTEM,
    render_template,
)

logger = get_logger(__name__)


def generator_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: генерация текста искового заявления."""
    logger.info("Generator node started")

    qa_feedback = state.get("qa_feedback", "")
    qa_attempts = state.get("qa_attempts", 0)

    variables = _collect_variables(state)

    # Если есть обратная связь от QA — используем доработочный промпт
    if qa_feedback and qa_attempts > 0:
        logger.info("  Re-generating after QA feedback (attempt %d)", qa_attempts)
        original_prompt = render_template(GENERATOR_HUMAN, variables)
        prompt = render_template(
            GENERATOR_REWORK_HUMAN,
            {
                "generated_document": state.get("generated_document", ""),
                "qa_feedback": qa_feedback,
                "original_prompt_data": original_prompt,
            },
        )
    else:
        prompt = render_template(GENERATOR_HUMAN, variables)

    try:
        content = invoke_llm([
            SystemMessage(content=GENERATOR_SYSTEM),
            HumanMessage(content=prompt),
        ])
        logger.info("  Document generated, length: %d chars", len(content))
        return {"generated_document": content}

    except Exception as e:
        logger.error("Generator failed: %s", e)
        return {"error": f"Ошибка генерации документа: {e}"}


def _collect_variables(state: AgentState) -> dict[str, Any]:
    """Собирает все переменные для подстановки в шаблон."""
    from app.modules.calculator_ import _fmt

    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    return {
        "plaintiff_info": state.get("plaintiff_info", "[НЕ УКАЗАНО]"),
        "defendant_info": state.get("defendant_info", "[НЕ УКАЗАНО]"),
        "third_parties_info": state.get("third_parties_info", "не заявлены"),
        "court_info": state.get("court_info", "[НЕ УКАЗАНО]"),
        "case_category": state.get("case_category", ""),
        "facts": state.get("facts", "[НЕ УКАЗАНО]"),
        "documents": state.get("documents", "[НЕ УКАЗАНО]"),
        "claims": state.get("claims", "[НЕ УКАЗАНО]"),
        "principal_amount": _amount("principal_amount"),
        "penalty_amount": _amount("penalty_amount"),
        "interest_amount": _amount("interest_amount"),
        "moral_damage": _amount("moral_damage"),
        "court_expenses": _amount("court_expenses"),
        "state_duty": _amount("state_duty"),
        "total_claim": _amount("total_claim"),
        "applicable_laws": state.get("applicable_laws", "[НЕ ОПРЕДЕЛЕНЫ]"),
        "legal_positions": state.get("legal_positions", ""),
        "pretrial_settlement": state.get("pretrial_settlement", "не проводилось"),
        "calculation_details": state.get("calculation_details", ""),
    }