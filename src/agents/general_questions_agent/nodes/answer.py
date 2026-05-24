import os
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM

from ...utils import update_tokens_metadata


ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_SYSTEM),
        MessagesPlaceholder("messages"),
    ]
)

logger = LoggerFactory.get_logger(
    name="GeneralQuestionsAgentAnswerNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def clear_before_end(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "raw_input": None,
    }


async def clear_previous_run_results(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": None,
        "reply": None,
    }


async def answer_node(
    state: GeneralQuestionAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> Dict[str, Any]:
    logger.info("Start")
    messages = list(state.get("messages") or [])
    if not messages:
        return {
            "error": "[general_questions_agent] empty input",
        }
    try:
        chain = ANSWER_PROMPT | llm
        response = await chain.ainvoke({"messages": messages}, config=config)
        reply = response.content or ""
        usage_metadata = getattr(response, "usage_metadata", None) or {}
        previous_usage_metadata = state.get("usage_metadata", {}) or {}
        usage_metadata = update_tokens_metadata(
            previous_usage_metadata,
            usage_metadata,
            ["input_tokens", "output_tokens", "total_tokens"],
        )
    except Exception as e:
        logger.error(f"[general_questions_agent] ainvoke error: {e}", exc_info=True)
        return {
            "error": "[general_questions_agent] ainvoke error",
        }
    logger.debug(f"Got result reply: {reply}")
    logger.info("Finish")
    return {
        "reply": reply,
        "messages": [AIMessage(content=reply)],
        "usage_metadata": usage_metadata,
    }
