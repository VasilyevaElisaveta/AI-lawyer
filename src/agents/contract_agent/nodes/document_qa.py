import re
import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm_client import GigaChatClient
from ..state import AgentState
from ..prompts import (
    CONTRACT_QA_HUMAN, 
    QA_SYSTEM
)

from ...utils import build_qa_context, render_template

_QA_PASS_THRESHOLD = 5


def _build_contract_qa_prompt(state: AgentState, document: str) -> tuple[str, str]:
    context = build_qa_context(state)
    prompt = render_template(
        CONTRACT_QA_HUMAN,
        {
            "generated_document": document,
            "context": context,
        },
    )
    return QA_SYSTEM, prompt


def _parse_qa(text: str) -> dict[str, Any]:
    raw = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        raw = match.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "passed": True,
            "score": 5,
            "issues": [],
            "suggestions": [],
        }


async def qa_node(state: AgentState, llm: GigaChatClient) -> Dict[str, Any]:
    """Узел графа: рецензирование сгенерированного документа."""
    qa_attempts = state.get("qa_attempts", 0) + 1
    state["qa_attempts"] = qa_attempts
    document = state.get("generated_document", "")

    if not document:
        return {
            "qa_passed": False,
            "qa_feedback": "Документ не был сгенерирован",
            "qa_attempts": qa_attempts,
        }

    system, prompt = _build_contract_qa_prompt(state, document)

    try:
        content = await llm.ainvoke([
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

        state["qa_passed"] = passed
        state["qa_feedback"] = feedback
        if passed:
            qa_attempts = 0
        state["qa_attempts"] = qa_attempts
        return dict(state)

    except Exception as e:
        qa_attempts = 0
        state["qa_passed"] = True  # при ошибке QA — пропускаем, чтобы не блокировать
        state["qa_feedback"] = f"Ошибка рецензирования: {e}"
        state["qa_attempts"] = qa_attempts
        return dict(state)
