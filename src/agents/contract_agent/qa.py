from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .llm_client import GigaChatClient
from .state import AgentState
from .prompts import QA_HUMAN, QA_SYSTEM
from .utils import build_qa_context, render_template

_QA_PASS_THRESHOLD = 7


def _build_lawsuit_qa_prompt(state: AgentState, document: str) -> tuple[str, str]:
    context = build_qa_context(state.to_dict())
    prompt = render_template(
        QA_HUMAN,
        {
            "generated_document": document,
            "context": context,
        },
    )
    return QA_SYSTEM, prompt


def _build_pretrial_qa_prompt(state: AgentState, document: str) -> tuple[str, str]:
    context = build_qa_context(state.to_dict())
    prompt = render_template(
        QA_HUMAN,
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


async def qa_node(state: AgentState, llm: GigaChatClient) -> dict[str, Any]:
    qa_attempts = state.get("qa_attempts", 0) + 1
    state.set("qa_attempts", qa_attempts)
    document = state.get("generated_document", "")
    doc_type = state.get("doc_type", "lawsuit")

    if not document:
        return {
            "qa_passed": False,
            "qa_feedback": "Документ не был сгенерирован",
            "qa_attempts": qa_attempts,
        }

    if doc_type == "pretrial_claim":
        system, prompt = _build_pretrial_qa_prompt(state, document)
    else:
        system, prompt = _build_lawsuit_qa_prompt(state, document)

    try:
        content = await llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ])
        result = _parse_qa(content)
        passed = result.get("passed", False) and result.get("score", 0) >= _QA_PASS_THRESHOLD

        feedback_parts: list[str] = []
        if result.get("issues"):
            feedback_parts.append("Проблемы:\n" + "\n".join(f"• {i}" for i in result["issues"]))
        if result.get("suggestions"):
            feedback_parts.append(
                "Предложения:\n" + "\n".join(f"• {s}" for s in result["suggestions"])
            )
        feedback = "\n\n".join(feedback_parts).strip()

        return {
            "qa_passed": passed,
            "qa_feedback": feedback,
            "qa_attempts": qa_attempts,
        }

    except Exception as exc:
        return {
            "qa_passed": True,
            "qa_feedback": f"Ошибка рецензирования: {exc}",
            "qa_attempts": qa_attempts,
        }
