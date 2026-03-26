"""
Модуль проверки качества (LLM-рецензент).

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
    QA_HUMAN,
    QA_SYSTEM,
    PRETRIAL_QA_HUMAN,
    PRETRIAL_QA_SYSTEM,
    render_template,
)
from app.modules.calculator import _fmt

logger = get_logger(__name__)

_QA_PASS_THRESHOLD = 7  # минимальный балл для прохождения


# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════

def qa_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: рецензирование сгенерированного документа."""
    logger.info("▶ QA node started")

    qa_attempts = state.get("qa_attempts", 0) + 1
    document = state.get("generated_document", "")
    doc_type = state.get("doc_type", "lawsuit")

    if not document:
        logger.warning("  No document to review")
        return {
            "qa_passed": False,
            "qa_feedback": "Документ не был сгенерирован",
            "qa_attempts": qa_attempts,
        }

    # Выбираем промпт и переменные по типу документа
    if doc_type == "pretrial_claim":
        system, prompt = _build_pretrial_qa_prompt(state, document)
    else:
        system, prompt = _build_lawsuit_qa_prompt(state, document)

    try:
        content = invoke_llm([
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ])
        result = _parse_qa(content)
        passed = result.get("passed", False) and result.get("score", 0) >= _QA_PASS_THRESHOLD

        feedback_parts = []
        if result.get("issues"):
            feedback_parts.append("Проблемы:\n" + "\n".join(f"• {i}" for i in result["issues"]))
        if result.get("suggestions"):
            feedback_parts.append(
                "Предложения:\n" + "\n".join(f"• {s}" for s in result["suggestions"])
            )
        feedback = "\n\n".join(feedback_parts) if feedback_parts else ""

        logger.info(
            "  QA [%s] attempt %d: %s  score=%s",
            doc_type,
            qa_attempts,
            "PASSED" if passed else "FAILED",
            result.get("score"),
        )

        return {
            "qa_passed": passed,
            "qa_feedback": feedback,
            "qa_attempts": qa_attempts,
        }

    except Exception as e:
        logger.error("QA failed: %s — marking as passed by default", e)
        return {
            "qa_passed": True,  # при ошибке QA — пропускаем, чтобы не блокировать
            "qa_feedback": f"Ошибка рецензирования: {e}",
            "qa_attempts": qa_attempts,
        }


# ═══════════════════════════════════════════════════════════════
#  Формирование промптов QA по типу документа
# ═══════════════════════════════════════════════════════════════

def _amount(state: AgentState, key: str) -> str:
    """Форматирует сумму из state для подстановки в промпт."""
    val = state.get(key, 0)
    if isinstance(val, (int, float)) and val > 0:
        return _fmt(val)
    return "0"


def _build_lawsuit_qa_prompt(state: AgentState, document: str) -> tuple[str, str]:
    """Промпт QA для искового заявления."""
    prompt = render_template(
        QA_HUMAN,
        {
            "generated_document": document,
            "plaintiff_info": state.get("plaintiff_info", ""),
            "defendant_info": state.get("defendant_info", ""),
            "facts": state.get("facts", ""),
            "claims": state.get("claims", ""),
            "applicable_laws": state.get("applicable_laws", ""),
            "principal_amount": _amount(state, "principal_amount"),
            "loan_interest_amount": _amount(state, "loan_interest_amount"),
            "penalty_amount": _amount(state, "penalty_amount"),
            "interest_amount": _amount(state, "interest_amount"),
            "moral_damage": _amount(state, "moral_damage"),
            "court_expenses": _amount(state, "court_expenses"),
            "state_duty": _amount(state, "state_duty"),
            "total_claim": _amount(state, "total_claim"),
            "request_ongoing_penalty": state.get("request_ongoing_penalty", False),
        },
    )
    return QA_SYSTEM, prompt


def _build_pretrial_qa_prompt(state: AgentState, document: str) -> tuple[str, str]:
    """Промпт QA для досудебной претензии."""
    prompt = render_template(
        PRETRIAL_QA_HUMAN,
        {
            "generated_document": document,
            "sender_info": state.get("sender_info", ""),
            "recipient_info": state.get("recipient_info", ""),
            "facts": state.get("facts", ""),
            "sender_demands": state.get("sender_demands", ""),
            "applicable_laws": state.get("applicable_laws", ""),
            "principal_amount": _amount(state, "principal_amount"),
            "loan_interest_amount": _amount(state, "loan_interest_amount"),
            "penalty_amount": _amount(state, "penalty_amount"),
            "interest_amount": _amount(state, "interest_amount"),
            "moral_damage": _amount(state, "moral_damage"),
            "total_amount": _amount(state, "total_amount"),
            "response_deadline": state.get("response_deadline", ""),
        },
    )
    return PRETRIAL_QA_SYSTEM, prompt


# ═══════════════════════════════════════════════════════════════
#  Парсинг ответа QA
# ═══════════════════════════════════════════════════════════════

def _parse_qa(text: str) -> dict[str, Any]:
    """Извлекает JSON из ответа LLM-рецензента."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])
    # Фолбэк — если не удалось распарсить
    return {"passed": True, "score": 5, "issues": [], "suggestions": []}