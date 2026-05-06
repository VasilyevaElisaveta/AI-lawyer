from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM, ANSWER_PROMPT

from ...utils import render_template

from ....utils import LoggerFactory

logger = LoggerFactory.get_logger("GeneralQuestionsAgentAnswerNode")


async def clear_previous_run_results(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": None,
        "reply": None,
        "raw_input": None,
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
        response = await llm.ainvoke([
            SystemMessage(content=ANSWER_SYSTEM),
            HumanMessage(content=prompt),
        ],
        config=config
        )
        reply = response.content
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
    }
