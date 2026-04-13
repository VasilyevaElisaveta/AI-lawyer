import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from .prompts import (
    CONTRACT_MARKDOWN_PROMPT,
    CONTRACT_MARKDOWN_SYSTEM,
)
from .documents_templates import CONTRACT_TEMPLATES


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:markdown|md)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _build_template_outline(state: dict) -> dict[str, Any]:
    contract_type = state.get("contract_type")
    template = CONTRACT_TEMPLATES.get(contract_type, {})
    collected = state.get("collected_fields", {}) or {}

    sections = []
    for section in template.get("sections", []):
        available_values = {
            field_id: collected[field_id]
            for field_id in section.get("field_ids", [])
            if field_id in collected and collected[field_id] not in (None, "", [], {})
        }
        sections.append({
            "id": section["id"],
            "heading": section["heading"],
            "label": section["label"],
            "required": section["required"],
            "field_ids": section.get("field_ids", []),
            "available_values": available_values,
            "instruction": section.get("instruction", ""),
        })

    return {
        "document_title": template.get("document_title", ""),
        "sections": sections,
    }


def _collect_generation_context(state: dict) -> dict[str, Any]:
    return {
        "contract_type": state.get("contract_type"),
        "document_title": CONTRACT_TEMPLATES.get(state.get("contract_type"), {}).get("document_title", ""),
        "collected_fields": state.get("collected_fields", {}) or {},
        "markdown_validation_errors": state.get("markdown_validation_errors", []) or [],
        "template_outline": _build_template_outline(state),
    }


async def contract_markdown_generation_node(state, llm):
    contract_type = state.get("contract_type")

    prompt = ChatPromptTemplate.from_messages([
        ("system", CONTRACT_MARKDOWN_SYSTEM),
        ("human", CONTRACT_MARKDOWN_PROMPT),
    ])
    chain = prompt | llm

    ctx = _collect_generation_context(state)
    raw = await chain.ainvoke({
        "contract_type": ctx["contract_type"],
        "template_outline": json.dumps(ctx["template_outline"], ensure_ascii=False, indent=2),
        "collected_fields": json.dumps(ctx["collected_fields"], ensure_ascii=False, indent=2),
        "markdown_validation_errors": json.dumps(ctx["markdown_validation_errors"], ensure_ascii=False, indent=2),
    })

    markdown = _strip_code_fence(raw)

    state["generated_markdown"] = markdown
    state["markdown_is_valid"] = False
    state["markdown_validation_errors"] = state.get("markdown_validation_errors", [])
    state.setdefault("generated_documents", [])
    state["generated_documents"] = state["generated_documents"] + [markdown]
    return state