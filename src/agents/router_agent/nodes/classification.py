from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from .prompts import (
    ROUTER_CLASSIFICATION_SYSTEM,
    ROUTER_CLASSIFICATION_PROMPT,
    CATEGORY_NOT_IMPLEMENTED,
    CLASSIFICATION_ERROR,
)

from ..state import RouterAgentState

from ...llm_client import GigaChatClient
from ...utils import safe_parse_json, render_template


async def classification_node(
        state: RouterAgentState, 
        llm: GigaChatClient, 
        previous_node: str | None = None
) -> Dict[str, Any]:
    """
    Узел классификации: определяет категорию запроса пользователя.
    
    Использует LLM для классификации в одну из 4 категорий:
    - contract (договоры)
    - lawsuit (иски)
    - pretrial_claim (досудебные претензии)
    - simple_question (простые вопросы)
    
    Возвращает обновлённое состояние с результатом классификации.
    """
    raw_input = state.get("raw_input", "")
    
    if not raw_input:
        return {
            "error_message": "Не получено сообщение пользователя",
            "reply": "Ошибка: пустой запрос",
            "routed_to": "none",
        }
    
    if previous_node is not None:
        return {
            "routed_to": previous_node,
            "reply": "",
        }
    
    prompt = ChatPromptTemplate.from_messages(
        ("system", ROUTER_CLASSIFICATION_SYSTEM),
        ("human", ROUTER_CLASSIFICATION_PROMPT)
    )
    
    try:
        response = await llm.ainvoke({
            "raw_input": raw_input
        })
        classification_result = safe_parse_json(response)
    except Exception as e:
        return {
            "error_message": f"Ошибка при классификации: {str(e)}",
            "reply": CLASSIFICATION_ERROR,
            "routed_to": "none",
        }
    
    if not classification_result or "category" not in classification_result:
        return {
            "error_message": "LLM вернул некорректный результат классификации",
            "reply": CLASSIFICATION_ERROR,
            "routed_to": "none",
        }
    
    category = classification_result.get("category", "simple_question")
    confidence = classification_result.get("confidence", 0.0)
    
    # Определяем, реализован ли обработчик для этой категории
    implemented_categories = {"contract"}
    is_implemented = category in implemented_categories
    
    # Подготавливаем результат
    result: Dict[str, Any] = {
        "category": category,
        "classification_confidence": confidence,
        "classification_result": classification_result,
        "is_implemented": is_implemented,
    }
    
    # Определяем маршрут и ответ
    if is_implemented:
        result["routed_to"] = {
            "contract": "contract_agent",
            "simple_question": "simple_question_agent",
        }.get(category, "none")
        result["reply"] = ""
    else:
        # Категория не реализована
        result["routed_to"] = "none"
        result["error_message"] = f"Категория '{category}' ещё не реализована"
        result["reply"] = render_template(
            CATEGORY_NOT_IMPLEMENTED,
            {"category": category}
        )
    
    return result
