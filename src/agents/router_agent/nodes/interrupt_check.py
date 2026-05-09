import os
import re
from typing import Any, Dict

from logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..state import RouterAgentState

from ...utils import safe_parse_json, update_tokens_metadata


logger = LoggerFactory.get_logger(
    name="RouterAgentInterruptCheckNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


# Регулярные выражения для команд прерывания
INTERRUPT_PATTERNS = [
    r'\b(отмена|стоп|прервать|остановить|прекратить)\b',
    r'\b(новая задача|новое задание|другая задача)\b',
    r'\b(я передумал|передумал|изменил решение)\b',
    r'\b(давай другое|давай по-другому|начнем заново)\b',
    r'\b(составить|сделать|подготовить)\s+(иск|договор|претензию|заявление)\b',  # новая задача
]


def _check_interrupt_by_patterns(raw_input: str) -> bool:
    """
    Проверяет сообщение на команды прерывания с помощью регулярных выражений.
    Возвращает True, если найдена команда прерывания.
    """
    for pattern in INTERRUPT_PATTERNS:
        if re.search(pattern, raw_input, re.IGNORECASE):
            logger.debug(f"Найдена команда прерывания по паттерну: {pattern}")
            return True
    return False


async def interrupt_check_node(
        state: RouterAgentState, 
        llm, 
        config: RunnableConfig | None = None
) -> Dict[str, Any]:
    """
    Узел проверки прерывания активной задачи.
    
    Сначала проверяет регулярными выражениями на явные команды прерывания.
    Если не найдено, использует LLM для классификации намерения.
    
    Возвращает обновлённое состояние с решением о прерывании или продолжении.
    """
    logger.info("Start interrupt check...")
    raw_input = state.get("raw_input", "")
    active_task = state.get("active_task", None)
    
    if not active_task:
        logger.warning("No active task, skipping interrupt check")
        return {
            "should_interrupt": False,
            "interrupt_reason": "no_active_task"
        }
    
    # Сначала проверка регулярками
    if _check_interrupt_by_patterns(raw_input):
        logger.info("Interrupt detected by patterns")
        return {
            "should_interrupt": True,
            "interrupt_reason": "pattern_match",
            "previous_active_task": active_task,  # Сохраняем предыдущую задачу
            "active_task": None,  # Сбрасываем активную задачу
            "task_context": {},
            "task_started_at": None,
        }
    
    # Если не найдено паттернами, используем LLM
    logger.info("No pattern match, using LLM for interrupt classification")
    
    system_prompt = f"""
    Ты — помощник для анализа намерений пользователя в чате.
    Текущая активная задача: {active_task}
    
    Проанализируй сообщение пользователя и определи, хочет ли он:
    1) interrupt_task - прервать текущую задачу и начать новую
    2) continue_task - продолжить текущую задачу
    
    Возвращай ТОЛЬКО валидный JSON без дополнительных комментариев.
    """
    
    human_prompt = """
    Сообщение пользователя: {raw_input}
    
    Верни JSON объект со СЛЕДУЮЩЕЙ СТРУКТУРОЙ:
    {{
      "intent": "interrupt_task" | "continue_task",
      "confidence": <число от 0.0 до 1.0>,
      "reasoning": "<краткое объяснение>"
    }}
    
    ПРАВИЛА:
    - interrupt_task: если пользователь явно хочет остановить текущую задачу, начать новую, изменить направление
    - continue_task: если сообщение продолжает текущую задачу или является ответом на предыдущий запрос
    - Если уверенность < 0.7, выбирай continue_task (безопаснее продолжить)
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])
    
    chain = prompt | llm
    try:
        response = await chain.ainvoke({
            "active_task": active_task,
            "raw_input": raw_input
        }, config=config)
        
        raw = response.content
        result = safe_parse_json(raw)
        usage_metadata = getattr(response, "usage_metadata", {})
        previous_usage_metadata = state.get("usage_metadata", {}) or {}
        usage_metadata = update_tokens_metadata(
            previous_usage_metadata, 
            usage_metadata, 
            ["input_tokens", "output_tokens", "total_tokens"]
        )
        
        if not result or "intent" not in result:
            logger.warning("Invalid LLM response for interrupt check, defaulting to continue")
            return {
                "should_interrupt": False,
                "interrupt_reason": "llm_error",
                "usage_metadata": usage_metadata
            }
        
        intent = result.get("intent", "continue_task")
        confidence = result.get("confidence", 0.0)
        
        should_interrupt = intent == "interrupt_task" and confidence >= 0.7
        
        logger.debug(f"LLM interrupt check: intent={intent}, confidence={confidence}, should_interrupt={should_interrupt}")
        
        if should_interrupt:
            return {
                "should_interrupt": True,
                "interrupt_reason": "llm_classification",
                "active_task": None,
                "task_context": {},
                "task_started_at": None,
                "usage_metadata": usage_metadata
            }
        else:
            return {
                "should_interrupt": False,
                "interrupt_reason": "continue_task",
                "usage_metadata": usage_metadata
            }
            
    except Exception as e:
        logger.error(f"Error in LLM interrupt check: {e}")
        return {
            "should_interrupt": False,
            "interrupt_reason": "llm_exception",
            "usage_metadata": state.get("usage_metadata", {})
        }