import os
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from .prompts import (
    ROUTER_CLASSIFICATION_SYSTEM,
    ROUTER_CLASSIFICATION_PROMPT,
)

from ..state import RouterAgentState

from ...utils import safe_parse_json, update_tokens_metadata


logger = LoggerFactory.get_logger(
    name="RouterAgentClassificationNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def clear_previous_run_results(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": None,
        "routed_to": None,
        "is_implemented": None,
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
    
    Использует LLM для классификации в одну из 4 категорий:
    - contract (договоры)
    - claim (иски)
    - pretrial_claim (досудебные претензии)
    - general_question (общие вопросы)
    
    Возвращает обновлённое состояние с результатом классификации.
    """
    logger.info("Start...")
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
    
    implemented_categories = {"claim", "general_question"}
    is_implemented = category in implemented_categories
    
    result: Dict[str, Any] = {
        "routed_to": {
            "claim": "claims_agent",
            "general_question": "general_questions_agent",
        }.get(category, None),
        "classification_confidence": confidence,
        "classification_result": classification_result,
        "is_implemented": is_implemented,
        "usage_metadata": usage_metadata,
    }
    
    if not is_implemented:
        result["routed_to"] = None
        result["error"] = f"[router_agent] '{category}' not implemented"
    logger.debug(
        f"Got result\n" \
        f"routed to: {result['routed_to']}"
    )
    logger.info("Finish")
    return result
