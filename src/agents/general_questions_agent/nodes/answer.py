import os
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM, ANSWER_PROMPT

from ...utils import render_template

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
        "usage_metadata": None,
    }


async def answer_node(
    state: GeneralQuestionAgentState,
    llm,
    config: RunnableConfig | None = None
) -> Dict[str, Any]:
    """
    Узел ответа на общий вопрос.
    
    Использует LLM для генерации ответа на вопрос пользователя.
    
    Args:
        state: Состояние агента
        llm: Клиент LLM
        
    Returns:
        Обновлённое состояние с ответом
    """
    logger.info("Start")
    user_question = state.get("raw_input", "")

    if not user_question:
        return {
            "error": "[general_questions_agent] empty input",
        }
    
    prompt = render_template(ANSWER_PROMPT, {"user_question": user_question})
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=ANSWER_SYSTEM),
                HumanMessage(content=prompt),
            ],
            config=config
        )
        reply = response.content
        usage_metadata = getattr(response, "usage_metadata", None) or {}
    except Exception as e:
        return {
            "error": "[general_questions_agent] ainvoke error",
        }

    messages = state.get("messages", []) or []
    messages.append(AIMessage(content=reply))
    logger.debug(f"Got result reply: {reply}")
    logger.info("Finish")
    return {
        "reply": reply,
        "messages": messages,
        "usage_metadata": usage_metadata,
    }
