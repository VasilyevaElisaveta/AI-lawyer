import os
from typing import Any

from logger import LoggerFactory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..field_schemas import AGENT_TASK_LABELS
from ..state import RouterAgentState
from ...utils import safe_parse_json, update_tokens_metadata
from .prompts import CONTINUE_TASK_SYSTEM, CONTINUE_TASK_PROMPT


logger = LoggerFactory.get_logger(
    name="RouterAgentContinueTaskNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def continue_task_node(
    state: RouterAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    Если current_agent задан — определяет, хочет ли пользователь продолжить текущую задачу.
    """
    current_agent = state.get("current_agent")
    if not current_agent:
        return {"continue_current_task": True}

    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {"continue_current_task": True}

    task_label = AGENT_TASK_LABELS.get(current_agent, current_agent)
    collected = state.get("agent_fields") or {}
    collected_str = "\n".join(
        f"- {key}: {value}" for key, value in collected.items() if value
    ) or "(пока нет)"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CONTINUE_TASK_SYSTEM),
            ("human", CONTINUE_TASK_PROMPT),
        ]
    )
    chain = prompt | llm

    try:
        response = await chain.ainvoke(
            {
                "task_label": task_label,
                "collected_fields": collected_str,
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
    except Exception as e:
        logger.error("Continue task check failed: %s", e)
        return {
            "continue_current_task": True,
            "routed_to": current_agent,
            "skip_classification": True,
        }

    wants_continue = bool(parsed.get("continue", True))
    logger.info(
        "Continue task check: agent=%s continue=%s",
        current_agent,
        wants_continue,
    )

    if wants_continue:
        return {
            "continue_current_task": True,
            "skip_classification": True,
            "routed_to": current_agent,
            "usage_metadata": usage_metadata,
        }

    return {
        "continue_current_task": False,
        "skip_classification": False,
        "current_agent": None,
        "agent_fields": {},
        "category": None,
        "document_type": None,
        "routed_to": None,
        "usage_metadata": usage_metadata,
    }
