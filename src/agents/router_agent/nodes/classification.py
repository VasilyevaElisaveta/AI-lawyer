import os
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from .prompts import (
    ROUTER_CLASSIFICATION_SYSTEM,
    ROUTER_CLASSIFICATION_PROMPT,
)

from ..field_schemas import CATEGORY_TO_DOCUMENT_TYPE
from ..state import RouterAgentState

from ...utils import safe_parse_json, update_tokens_metadata


logger = LoggerFactory.get_logger(
    name="RouterAgentClassificationNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

_CATEGORY_TO_AGENT: dict[str, str] = {
    "claim": "claims_agent",
    "pretrial_claim": "claims_agent",
    "general_question": "general_questions_agent",
}

_IMPLEMENTED_CATEGORIES = {"claim", "pretrial_claim", "general_question"}


async def clear_previous_run_results(state: Dict[str, Any]) -> Dict[str, Any]:
    """Сбрасывает поля одного прогона, сохраняя межсессионное состояние задачи."""
    return {
        "error": None,
        "routed_to": None,
        "is_implemented": None,
        "fields_complete": None,
        "missing_fields_reply": None,
        "skip_classification": None,
        "continue_current_task": None,
        "usage_metadata": {},
    }


async def clear_before_end(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "raw_input": None,
    }


async def classification_node(
        state: RouterAgentState,
        llm,
        config: RunnableConfig | None = None
) -> Dict[str, Any]:
    """
    Узел классификации: определяет категорию запроса пользователя.
    Пропускается, если skip_classification=True (продолжение текущей задачи).
    """
    if state.get("skip_classification") and state.get("routed_to"):
        logger.info("Classification skipped — continuing task for %s", state.get("routed_to"))
        return {}

    logger.info("Classification started")
    raw_input = state.get("raw_input", "")

    if not raw_input:
        return {
            "error": "[router_agent] empty input",
        }

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_CLASSIFICATION_SYSTEM),
            ("human", ROUTER_CLASSIFICATION_PROMPT)
        ]
    )

    chain = prompt | llm
    try:
        response = await chain.ainvoke(
            {
                "raw_input": raw_input
            },
            config=config
        )
        raw = response.content
        classification_result = safe_parse_json(raw)
        usage_metadata = getattr(response, "usage_metadata", {})
        previous_usage_metadata = state.get("usage_metadata", {}) or {}
        usage_metadata = update_tokens_metadata(
            previous_usage_metadata,
            usage_metadata,
            ["input_tokens", "output_tokens", "total_tokens"]
        )
    except Exception as e:
        logger.error(f"Got error {e}")
        return {
            "error": "[router_agent] ainvoke error",
        }

    if not classification_result or "category" not in classification_result:
        return {
            "routed_to": None,
        }

    category = classification_result.get("category", "general_question")
    confidence = classification_result.get("confidence", 0.0)

    is_implemented = category in _IMPLEMENTED_CATEGORIES
    routed_to = _CATEGORY_TO_AGENT.get(category)
    document_type = CATEGORY_TO_DOCUMENT_TYPE.get(category)

    result: Dict[str, Any] = {
        "category": category,
        "routed_to": routed_to,
        "document_type": document_type,
        "classification_confidence": confidence,
        "classification_result": classification_result,
        "is_implemented": is_implemented,
        "usage_metadata": usage_metadata,
    }

    if not is_implemented:
        result["routed_to"] = None
        result["error"] = f"[router_agent] '{category}' not implemented"
    logger.debug(
        "Classification result: category=%s routed_to=%s",
        category,
        result["routed_to"],
    )
    logger.info("Classification finished")
    return result
