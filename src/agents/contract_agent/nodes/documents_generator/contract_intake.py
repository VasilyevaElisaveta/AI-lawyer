import json
from pathlib import Path
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate

from .prompts import (
    CLASSIFY_SYSTEM, CLASSIFY_PROMPT, EXTRACT_SYSTEM, EXTRACT_PROMPT
)
from .contract_fields import CONTRACT_FIELDS

from ....utils import safe_parse_json


def _get_missing_fields(state):
    contract_type = state.get("contract_type")
    collected = state.get("collected_fields", {})

    if not contract_type:
        return []

    schema = CONTRACT_FIELDS.get(contract_type, {})

    required = [f["id"] for f in schema.get("required", [])]
    optional = [f["id"] for f in schema.get("optional", [])]

    return [f for f in required + optional if f not in collected]


def _update_collected_fields(state, new_data):
    collected = state.get("collected_fields", {})
    collected.update(new_data)
    return collected


async def contract_intake_node(state, llm):
    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {"error": "Нет входных данных. Передайте raw_input."}

    contract_type = state.get("contract_type")
    collected_fields = state.get("collected_fields", {})

    d = {}

    if not contract_type:
        prompt = ChatPromptTemplate.from_messages([
            ("system", CLASSIFY_SYSTEM),
            ("human", CLASSIFY_PROMPT),
        ])

        chain = prompt | llm

        raw = await chain.ainvoke({
            "raw_input": raw_input
        })

        parsed = safe_parse_json(raw)
        new_type = parsed.get("contract_type")

        if new_type:
            contract_type = new_type
            d["contract_type"] = new_type
            d["contract_fields"] = CONTRACT_FIELDS.get(new_type, {})

    # если тип так и не определился — дальше смысла нет
    if not contract_type:
        state.update(d)
        return state

    target_fields = _get_missing_fields(state)

    if target_fields:
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACT_SYSTEM),
            ("human", EXTRACT_PROMPT),
        ])

        chain = prompt | llm

        raw = await chain.ainvoke({
            "existing_fields": json.dumps(collected_fields, ensure_ascii=False),
            "target_fields": target_fields,
            "raw_input": raw_input,
        })

        parsed = safe_parse_json(raw)
        new_fields = parsed.get("fields", {})

        if new_fields:
            updated = _update_collected_fields(state, new_fields)
            d["collected_fields"] = updated

    d["doc_type"] = "contract"

    state.update(d)
    return state


def validation_router(state) -> Literal["generation", "final"]:
    contract_type = state.get("contract_type")
    collected = state.get("collected_fields", {})
    if not contract_type:
        return "final"
    schema = state.get("contract_fields", {})
    required_fields = [f["id"] for f in schema.get("required", [])]
    missing_required = [f for f in required_fields if f not in collected]
    if missing_required:
        state["validation_errors"] = missing_required
        state["is_valid"] = False
        return "final"
    state["validation_errors"] = []
    state["is_valid"] = True
    return "generation"