import json
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate

from .prompts import (
    CLASSIFY_SYSTEM, CLASSIFY_PROMPT, EXTRACT_SYSTEM, EXTRACT_PROMPT
)
from .contract_fields import CONTRACT_FIELDS

from ....utils import safe_parse_json, messages_to_str


def _clear_previous_run_results(state):
    state["generated_docx_base64"] = None
    state["response_to_user"] = None
    state["markdown_generation_attempts"] = 0


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


async def contract_generator_intake_node(state, llm):
    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {"error": "Нет входных данных. Передайте raw_input."}
    messages = state.get("messages", [])
    messages_str = messages_to_str(messages)
    conversation_summary = state.get("conversation_summary", "")

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
            "raw_input": raw_input,
            "messages_str": messages_str,
            "conversation_summary": conversation_summary,

        })

        parsed = safe_parse_json(raw)
        new_type = parsed.get("contract_type")

        if new_type:
            contract_type = new_type
            d["contract_type"] = new_type
            d["contract_fields"] = CONTRACT_FIELDS.get(new_type, {})
    
    _clear_previous_run_results(state)

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
            "messages_str": messages_str,
            "conversation_summary": conversation_summary,
        })

        parsed = safe_parse_json(raw)
        new_fields = parsed.get("fields", {})

        if new_fields:
            updated = _update_collected_fields(state, new_fields)
            d["collected_fields"] = updated

    d["doc_type"] = "contract"
    d["current_node"] = "contract"

    state.update(d)
    return state


def contract_generator_validation_router(state) -> Literal["generation", "final"]:
    contract_type = state.get("contract_type")
    collected = state.get("collected_fields", {})
    if not contract_type:
        state["is_valid"] = False
        state["response_to_user"] = "Не удалось определить тип договора. Пожалуйста, уточните запрос."
        return "final"
    schema = state.get("contract_fields", {})
    required_fields = schema.get("required", [])
    field_map = {f["id"]: f["title"] for f in required_fields}
    missing_required = [
        f["id"] for f in required_fields
        if f["id"] not in collected
    ]
    if missing_required:
        missing_titles = [
            field_map.get(field_id, field_id)
            for field_id in missing_required
        ]
        response_message = (
            "Для формирования договора необходимо указать:\n\n"
            + "\n".join(f"- {title}" for title in missing_titles)
        )
        state["validation_errors"] = missing_required
        state["is_valid"] = False
        state["response_to_user"] = response_message
        return "final"
    state["validation_errors"] = []
    state["is_valid"] = True
    state["response_to_user"] = None
    return "generation"