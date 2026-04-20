from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM, ANSWER_PROMPT

from ...utils import render_template

from ....utils import LoggerFactory

logger = LoggerFactory.get_logger("GeneralQuestionsAgentAnswerNode")


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
            "reply": "Пожалуйста, задайте вопрос."
        }
    
    # Подготавливаем промпт
    prompt = render_template(ANSWER_PROMPT, {"user_question": user_question})
    
    # Вызываем LLM для генерации ответа
    try:
        response = await llm.ainvoke([
            SystemMessage(content=ANSWER_SYSTEM),
            HumanMessage(content=prompt),
        ],
        config=config
        )
        reply = response.content
    except Exception as e:
        reply = f"Ошибка при обработке вашего вопроса: {str(e)}"

    messages = state.get("messages", []) or []
    messages.append(AIMessage(content=reply))
    state["messages"] = messages
    logger.debug(f"Got result reply: {reply}")
    logger.info("Finish")
    return {
        "reply": reply,
        "messages": messages,
    }
