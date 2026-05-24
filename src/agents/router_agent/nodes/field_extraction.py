import json
import os
from typing import Any

from logger import LoggerFactory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..field_schemas import (
    AGENT_FIELD_SCHEMAS,
    CATEGORY_TO_DOCUMENT_TYPE,
    AgentFieldSpec,
    build_missing_fields_message,
    is_field_filled,
)
from ..state import RouterAgentState
from ...utils import safe_parse_json, update_tokens_metadata
from .prompts import FIELD_EXTRACTION_SYSTEM, FIELD_EXTRACTION_PROMPT


logger = LoggerFactory.get_logger(
    name="RouterAgentFieldExtractionNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

_TASK_DESCRIPTIONS: dict[str, str] = {
    "claims_agent": "исковое заявление или досудебная претензия",
    "general_questions_agent": "консультация по общему юридическому вопросу",
}


def _merge_fields(existing: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in extracted.items():
        if is_field_filled(value):
            merged[key] = value
    return merged


def _missing_required(
    schema: list[AgentFieldSpec],
    fields: dict[str, Any],
) -> list[AgentFieldSpec]:
    missing: list[AgentFieldSpec] = []
    for spec in schema:
        if not spec.required:
            continue
        if not is_field_filled(fields.get(spec.key)):
            missing.append(spec)
    return missing


async def _extract_with_llm(
    state: RouterAgentState,
    llm,
    agent: str,
    schema: list[AgentFieldSpec],
    known_fields: dict[str, Any],
    config: RunnableConfig | None,
) -> dict[str, Any]:
    raw_input = state.get("raw_input", "")
    fields_description = "\n".join(
        f'- "{spec.key}": {spec.description}' for spec in schema
    )
    known_str = json.dumps(known_fields, ensure_ascii=False, indent=2)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", FIELD_EXTRACTION_SYSTEM),
            ("human", FIELD_EXTRACTION_PROMPT),
        ]
    )
    chain = prompt | llm
    response = await chain.ainvoke(
        {
            "task_description": _TASK_DESCRIPTIONS.get(agent, agent),
            "fields_description": fields_description,
            "known_fields": known_str,
            "raw_input": raw_input,
        },
        config=config,
    )
    parsed = safe_parse_json(response.content)
    usage_metadata = getattr(response, "usage_metadata", {}) or {}
    previous_usage = state.get("usage_metadata", {}) or {}
    usage_metadata = update_tokens_metadata(
        previous_usage,
        usage_metadata,
        ["input_tokens", "output_tokens", "total_tokens"],
    )
    return {"fields": parsed, "usage_metadata": usage_metadata}


async def field_extraction_node(
    state: RouterAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    Извлекает поля для выбранного агента и проверяет обязательные.
    При нехватке данных формирует стандартный ответ без генерации LLM-ответа.
    """
    routed_to = state.get("routed_to") or state.get("current_agent")
    if not routed_to:
        return {"error": "[router_agent] agent not selected for field extraction"}

    schema = AGENT_FIELD_SCHEMAS.get(routed_to)
    if not schema:
        return {
            "fields_complete": True,
            "current_agent": routed_to,
            "agent_fields": state.get("agent_fields") or {},
        }

    known_fields: dict[str, Any] = dict(state.get("agent_fields") or {})
    raw_input = state.get("raw_input", "")

    usage_metadata = state.get("usage_metadata", {}) or {}

    if routed_to == "general_questions_agent":
        if raw_input:
            known_fields["question"] = raw_input.strip()
    else:
        try:
            extraction = await _extract_with_llm(
                state, llm, routed_to, schema, known_fields, config
            )
            known_fields = _merge_fields(known_fields, extraction.get("fields", {}))
            usage_metadata = extraction.get("usage_metadata", usage_metadata)
        except Exception as e:
            logger.error("Field extraction failed: %s", e)
            if raw_input and routed_to == "claims_agent":
                known_fields.setdefault("facts", raw_input)

    document_type = state.get("document_type")
    category = state.get("category")
    if routed_to == "claims_agent":
        if not document_type and category:
            document_type = CATEGORY_TO_DOCUMENT_TYPE.get(category, "lawsuit")
        if document_type:
            known_fields["document_type"] = document_type

    missing = _missing_required(schema, known_fields)

    if missing:
        reply = build_missing_fields_message(routed_to, missing)
        logger.info(
            "Fields incomplete for %s, missing: %s",
            routed_to,
            [m.key for m in missing],
        )
        return {
            "agent_fields": known_fields,
            "current_agent": routed_to,
            "fields_complete": False,
            "missing_fields_reply": reply,
            "document_type": document_type,
            "usage_metadata": usage_metadata,
        }

    logger.info("All required fields collected for %s", routed_to)
    return {
        "agent_fields": known_fields,
        "current_agent": routed_to,
        "fields_complete": True,
        "missing_fields_reply": None,
        "document_type": document_type,
        "usage_metadata": usage_metadata,
    }
