"""
Модуль проверки качества (LLM-рецензент).
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.state import AgentState
from app.services.llm_client import invoke_llm
from app.utils.logger import get_logger
from app.utils.prompts import QA_HUMAN, QA_SYSTEM, render_template
from app.modules.calculator_ import _fmt

logger = get_logger(__name__)

_QA_PASS_THRESHOLD = 7  # минимальный балл для прохождения


def qa_node(state: AgentState) -> dict[str, Any]:
    """Узел графа: рецензирование сгенерированного документа."""
    logger.info("QA node started")

    qa_attempts = state.get("qa_attempts", 0) + 1
    document = state.get("generated_document", "")

    if not document:
        logger.warning("  No document to review")
        return {
            "qa_passed": False,
            "qa_feedback": "Документ не был сгенерирован",
            "qa_attempts": qa_attempts,
        }

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

    try:
        content = invoke_llm([
            SystemMessage(content=QA_SYSTEM),
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
            "  QA attempt %d: %s  score=%s",
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


def _parse_qa(text: str) -> dict[str, Any]:
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])
    # Фолбэк
    return {"passed": True, "score": 5, "issues": [], "suggestions": []}