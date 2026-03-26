"""
Модуль генерации документа.
Формирует промпт из всех данных state и вызывает LLM.

Поддерживает два типа документов:
  • lawsuit        — исковое заявление
  • pretrial_claim — досудебная претензия
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
    PRETRIAL_GENERATOR_HUMAN,
    PRETRIAL_GENERATOR_SYSTEM,
    render_template,
)

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def generator_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: генерация текста документа."""
    logger.info("▶ Generator node started")

    doc_type = state.get("doc_type", "lawsuit")
    qa_feedback = state.get("qa_feedback", "")
    qa_attempts = state.get("qa_attempts", 0)

    # Выбираем промпт и переменные по типу документа
    if doc_type == "pretrial_claim":
        variables = _collect_pretrial_variables(state)
        system = PRETRIAL_GENERATOR_SYSTEM
        human_template = PRETRIAL_GENERATOR_HUMAN
    else:
        variables = _collect_lawsuit_variables(state)
        system = GENERATOR_SYSTEM
        human_template = GENERATOR_HUMAN

    # Если есть обратная связь от QA — используем доработочный промпт
    if qa_feedback and qa_attempts > 0:
        logger.info("  Re-generating after QA feedback (attempt %d)", qa_attempts)
        original_prompt = render_template(human_template, variables)
        prompt = render_template(
            GENERATOR_REWORK_HUMAN,
            {
                "generated_document": state.get("generated_document", ""),
                "qa_feedback": qa_feedback,
                "original_prompt_data": original_prompt,
            },
        )
    else:
        prompt = render_template(human_template, variables)

    try:
        content = invoke_llm([
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ])
        logger.info("  Document generated [%s], length: %d chars", doc_type, len(content))
        return {"generated_document": content}

    except Exception as e:
        logger.error("Generator failed: %s", e)
        return {"error": f"Ошибка генерации документа: {e}"}


# ═══════════════════════════════════════════════════════════════
#  Сбор переменных для искового заявления
# ═══════════════════════════════════════════════════════════════

def _collect_lawsuit_variables(state: AgentState) -> dict[str, Any]:
    """Собирает все переменные для подстановки в шаблон иска."""
    from app.modules.calculator import _fmt

    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    # Текст о взыскании по день фактического исполнения
    ongoing_parts = []
    if state.get("request_ongoing_penalty"):
        rate = state.get("penalty_rate", 0)
        if rate:
            ongoing_parts.append(
                f"Заявить требование о взыскании неустойки ({rate * 100:.4g}% в день) "
                f"по день фактического исполнения обязательства."
            )
    if state.get("request_ongoing_interest"):
        loan_rate = state.get("loan_interest_rate", 0)
        if loan_rate:
            ongoing_parts.append(
                f"Заявить требование о взыскании процентов за пользование займом "
                f"({loan_rate * 100:.2f}% годовых) по день фактического возврата займа."
            )
    ongoing_text = "\n".join(ongoing_parts) if ongoing_parts else "Не требуется"

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
        "loan_interest_amount": _amount("loan_interest_amount"),
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
        "ongoing_claims_text": ongoing_text,
        "request_ongoing_penalty": state.get("request_ongoing_penalty", False),
    }


# ═══════════════════════════════════════════════════════════════
#  Сбор переменных для претензии
# ═══════════════════════════════════════════════════════════════

def _collect_pretrial_variables(state: AgentState) -> dict[str, Any]:
    """Собирает все переменные для подстановки в шаблон претензии."""
    from app.modules.calculator import _fmt

    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    return {
        "sender_info": state.get("sender_info", "[НЕ УКАЗАНО]"),
        "recipient_info": state.get("recipient_info", "[НЕ УКАЗАНО]"),
        "claim_type": state.get("claim_type", ""),
        "basis": state.get("basis", ""),
        "facts": state.get("facts", "[НЕ УКАЗАНО]"),
        "supporting_documents": state.get("supporting_documents", "[НЕ УКАЗАНО]"),
        "sender_demands": state.get("sender_demands", "[НЕ УКАЗАНО]"),
        "response_deadline": state.get(
            "response_deadline",
            "10 календарных дней с момента получения настоящей претензии",
        ),
        "principal_amount": _amount("principal_amount"),
        "loan_interest_amount": _amount("loan_interest_amount"),
        "penalty_amount": _amount("penalty_amount"),
        "interest_amount": _amount("interest_amount"),
        "moral_damage": _amount("moral_damage"),
        "total_amount": _amount("total_amount"),
        "applicable_laws": state.get("applicable_laws", "[НЕ ОПРЕДЕЛЕНЫ]"),
        "legal_positions": state.get("legal_positions", ""),
        "calculation_details": state.get("calculation_details", ""),
    }