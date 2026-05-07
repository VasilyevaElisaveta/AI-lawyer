import os
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..state import GeneralQuestionAgentState
from ..prompts import ANSWER_SYSTEM, ANSWER_PROMPT

from ...utils import render_template, messages_to_str, update_tokens_metadata


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
    messages = state.get("messages", []) or []
    messages_str = messages_to_str(messages)
    conversation_summary = state.get("conversation_summary", "")

    if not user_question:
        return {
            "error": "[general_questions_agent] empty input",
        }
    
    prompt = render_template(ANSWER_PROMPT, {"user_question": user_question})
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANSWER_SYSTEM),
            ("human", ANSWER_PROMPT)
        ]
    )

    chain = prompt | llm
    try:
        response = await chain.ainvoke(
            {
                "user_question": user_question,
                "messages_str": messages_str,
                "conversation_summary": conversation_summary,
            },
            config=config
        )
        reply = response.content
        usage_metadata = getattr(response, "usage_metadata", None) or {}
        previous_usage_metadata = state.get("usage_metadata", {})
        usage_metadata = update_tokens_metadata(
            previous_usage_metadata, 
            usage_metadata, 
            ["input_tokens", "output_tokens", "total_tokens"]
        )
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
