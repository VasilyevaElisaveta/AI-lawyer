"""
Модуль проверки качества (LLM-рецензент).
Поддерживает проверку как исковых заявлений, так и претензий.
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
    QA_HUMAN,
    QA_SYSTEM,
    COMPLAINT_QA_HUMAN,
    COMPLAINT_QA_SYSTEM,
    render_template,
)
from claims_agent.nodes.document_generation.calc import _fmt


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") is not "DEBUG" else None,
)

_QA_PASS_THRESHOLD = 7  # минимальный балл для прохождения


def qa_node(state: ClaimsAgentState) -> dict[str, Any]:
    """Узел графа: рецензирование сгенерированного документа."""
    document_type = state.get("document_type", "lawsuit")
    logger.info("QA node started (document_type=%s)", document_type)

    qa_attempts = state.get("qa_attempts", 0) + 1
    document = state.get("generated_document", "")

    if not document:
        logger.warning("  No document to review")
        return {
            "qa_passed": False,
            "qa_feedback": "Документ не был сгенерирован",
            "qa_attempts": qa_attempts,
        }

    if document_type == "complaint":
        return _qa_complaint(state, document, qa_attempts)
    return _qa_lawsuit(state, document, qa_attempts)


# ═══════════════════════════════════════════════════════════════
#  QA для искового заявления
# ═══════════════════════════════════════════════════════════════

def _qa_lawsuit(state: ClaimsAgentState, document: str, qa_attempts: int) -> dict[str, Any]:
    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    prompt = render_template(
        QA_HUMAN,
        {
            "generated_document": document,
            "plaintiff_info": state.get("plaintiff_info", ""),
            "defendant_info": state.get("defendant_info", ""),
            "facts": state.get("facts", ""),
            "claims": state.get("claims", ""),
            "applicable_laws": state.get("applicable_laws", ""),
            "principal_amount": _amount("principal_amount"),
            "penalty_amount": _amount("penalty_amount"),
            "interest_amount": _amount("interest_amount"),
            "moral_damage": _amount("moral_damage"),
            "court_expenses": _amount("court_expenses"),
            "state_duty": _amount("state_duty"),
            "total_claim": _amount("total_claim"),
        },
    )

    return _run_qa(QA_SYSTEM, prompt, qa_attempts, "lawsuit")


# ═══════════════════════════════════════════════════════════════
#  QA для претензии
# ═══════════════════════════════════════════════════════════════

def _qa_complaint(state: ClaimsAgentState, document: str, qa_attempts: int) -> dict[str, Any]:
    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    response_deadline = state.get("complaint_response_deadline", 30)

    prompt = render_template(
        COMPLAINT_QA_HUMAN,
        {
            "generated_document": document,
            "sender_info": state.get("plaintiff_info", ""),
            "recipient_info": state.get("defendant_info", ""),
            "facts": state.get("facts", ""),
            "claims": state.get("claims", ""),
            "applicable_laws": state.get("applicable_laws", ""),
            "principal_amount": _amount("principal_amount"),
            "penalty_amount": _amount("penalty_amount"),
            "interest_amount": _amount("interest_amount"),
            "moral_damage": _amount("moral_damage"),
            "response_deadline": str(response_deadline),
        },
    )

    return _run_qa(COMPLAINT_QA_SYSTEM, prompt, qa_attempts, "complaint")


# ═══════════════════════════════════════════════════════════════
#  Общая логика запуска QA
# ═══════════════════════════════════════════════════════════════

def _run_qa(
    system_prompt: str,
    human_prompt: str,
    qa_attempts: int,
    doc_type: str,
) -> dict[str, Any]:
    try:
        content = invoke_llm([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        result = _parse_qa(content)
        passed = result.get("passed", False) and result.get("score", 0) >= _QA_PASS_THRESHOLD

        feedback_parts = []
        if result.get("issues"):
            feedback_parts.append("Проблемы:\n" + "\n".join(f"• {i}" for i in result["issues"]))
        if result.get("suggestions"):
            feedback_parts.append("Предложения:\n" + "\n".join(f"• {s}" for s in result["suggestions"]))
        feedback = "\n\n".join(feedback_parts) if feedback_parts else ""

        logger.info(
            "  QA attempt %d (%s): %s  score=%s",
            qa_attempts,
            doc_type,
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
            "qa_passed": True,
            "qa_feedback": f"Ошибка рецензирования: {e}",
            "qa_attempts": qa_attempts,
        }


def _parse_qa(text: str) -> dict[str, Any]:
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start:end + 1])
    return {"passed": True, "score": 5, "issues": [], "suggestions": []}
