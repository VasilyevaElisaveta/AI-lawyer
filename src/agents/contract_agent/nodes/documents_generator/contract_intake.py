import json
from typing import Any, Dict, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from .prompts import CLASSIFY_SYSTEM, CLASSIFY_PROMPT, EXTRACT_SYSTEM, EXTRACT_PROMPT
from .contract_fields import CONTRACT_FIELDS

from ....utils import safe_parse_json, messages_to_str

from .....utils import LoggerFactory


logger = LoggerFactory.get_logger("ContractAgentDocumentGeneratorIntakeNode")


def _clear_previous_run_results(update: Dict[str, Any]) -> None:
    update["generated_docx_base64"] = None
    update["response_to_user"] = None
    update["markdown_generation_attempts"] = 0
    logger.info("Previous run results cleared")


def _get_missing_fields(state: Dict[str, Any]) -> list[str]:
    contract_type = state.get("contract_type")
    collected = state.get("collected_fields", {})
    if not contract_type:
        return []
    schema = CONTRACT_FIELDS.get(contract_type, {})
    required = [f["id"] for f in schema.get("required", [])]
    optional = [f["id"] for f in schema.get("optional", [])]
    return [f for f in required + optional if f not in collected]


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _update_collected_fields(state: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    collected = dict(state.get("collected_fields", {}) or {})
    for key, value in (new_data or {}).items():
        if _is_filled(value):
            collected[key] = value
    return collected


async def contract_generator_intake_node(
    state,
    llm,
    config: RunnableConfig | None = None
):
    logger.info("Start...")

    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {
            "error": "Нет входных данных. Передайте raw_input.",
            "response_to_user": "Нет входных данных. Передайте raw_input.",
            "is_valid": False,
        }

    messages = state.get("messages", []) or []
    messages_str = messages_to_str(messages)
    conversation_summary = state.get("conversation_summary", "")

    updates: Dict[str, Any] = {}
    _clear_previous_run_results(updates)

    contract_type = state.get("contract_type")
    collected_fields = state.get("collected_fields", {})
    logger.debug(f"Got START collected_fields: {collected_fields}")

    if not contract_type:
        prompt = ChatPromptTemplate.from_messages([
            ("system", CLASSIFY_SYSTEM),
            ("human", CLASSIFY_PROMPT),
        ])
        chain = prompt | llm

        response = await chain.ainvoke(
            {
                "raw_input": raw_input,
                "messages_str": messages_str,
                "conversation_summary": conversation_summary,
            },
            config=config,
        )

        parsed = safe_parse_json(response.content)
        new_type = parsed.get("contract_type")
        logger.debug(f"Got contract type: {new_type}")

        if new_type:
            contract_type = new_type
            updates["contract_type"] = new_type
            updates["contract_fields"] = CONTRACT_FIELDS.get(new_type, {})

    merged_state = {**state, **updates}
    merged_state["contract_type"] = contract_type
    merged_state["collected_fields"] = collected_fields

    if not contract_type:
        updates["doc_type"] = "contract"
        updates["current_node"] = "contract"
        updates["is_valid"] = False
        updates["response_to_user"] = "Не удалось определить тип договора. Пожалуйста, уточните запрос."
        logger.warning("Unable to identify contract type")
        logger.info("Finish")
        return updates

    target_fields = _get_missing_fields(merged_state)
    logger.debug(f"Get target fields: {target_fields}")

    if target_fields:
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACT_SYSTEM),
            ("human", EXTRACT_PROMPT),
        ])
        chain = prompt | llm

        response = await chain.ainvoke(
            {
                "existing_fields": json.dumps(collected_fields, ensure_ascii=False),
                "target_fields": target_fields,
                "raw_input": raw_input,
                "messages_str": messages_str,
                "conversation_summary": conversation_summary,
            },
            config=config,
        )

        parsed = safe_parse_json(response.content)
        new_fields = parsed.get("fields", {}) or {}

        updates["collected_fields"] = dict(collected_fields)

        if new_fields:
            updates["collected_fields"] = _update_collected_fields(merged_state, new_fields)

    updates["doc_type"] = "contract"
    updates["current_node"] = "contract"

    logger.debug(f"Got result collected_fields: {updates.get('collected_fields', collected_fields)}")
    logger.info("Finish")
    return updates


async def contract_generator_intake_validation_node(state) -> Dict[str, Any]:
    logger.info("Start...")

    contract_type = state.get("contract_type")
    collected = state.get("collected_fields", {}) or {}
    schema = state.get("contract_fields", {}) or {}

    base = {
        "contract_type": contract_type,
        "contract_fields": schema,
        "collected_fields": collected,
        "doc_type": state.get("doc_type", "contract"),
        "current_node": state.get("current_node", "contract"),
    }

    if not contract_type:
        return {
            **base,
            "is_valid": False,
            "validation_errors": [],
            "response_to_user": "Не удалось определить тип договора. Пожалуйста, уточните запрос.",
        }

    required_fields = schema.get("required", [])
    field_map = {f["id"]: f["title"] for f in required_fields}
    missing_required = [
        f["id"] for f in required_fields
        if not _is_filled(collected.get(f["id"]))
    ]

    if missing_required:
        missing_titles = [field_map.get(field_id, field_id) for field_id in missing_required]
        response_message = (
            "Для формирования договора необходимо указать:\n\n"
            + "\n".join(f"- {title}" for title in missing_titles)
        )

        logger.debug(f"Missing required fields: {missing_required}")
        logger.debug(f"Response to user: {response_message}")

        return {
            **base,
            "validation_errors": missing_required,
            "is_valid": False,
            "response_to_user": response_message,
        }

    logger.debug("Validation passed")
    return {
        **base,
        "validation_errors": [],
        "is_valid": True,
        "response_to_user": None,
    }


def contract_generator_validation_router(
    state
) -> Literal["markdown_generation", "generator_final"]:
    logger.info("Start router...")

    if not state.get("is_valid"):
        logger.debug("Selected node: generator_final")
        logger.info("Finish router")
        return "generator_final"

    logger.debug("Selected node: markdown_generation")
    logger.info("Finish router")
    return "markdown_generation"