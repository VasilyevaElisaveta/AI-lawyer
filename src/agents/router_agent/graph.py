from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from .nodes import classification_node
from .state import RouterAgentState
from ..llm_client import GigaChatClient


def create_graph(llm: GigaChatClient) -> StateGraph:
    """
    Создаёт граф маршрутизирующего агента.
    
    Граф состоит из одного узла:
    1. classification - классификация запроса пользователя в одну из 4 категорий
    
    После классификации граф завершает работу, передавая результат классификации.
    """
    graph = StateGraph(RouterAgentState)

    # Добавляем узел классификации
    graph.add_node("classification", partial(classification_node, llm=llm))

    # Определяем рёбра
    graph.add_edge(START, "classification")
    graph.add_edge("classification", END)

    return graph


class RouterAgent:
    """
    Маршрутизирующий агент на основе LanggGraph.
    
    Ответственен за:
    1. Классификацию входящих запросов в одну из 4 категорий
    2. Определение, реализован ли обработчик для данной категории
    3. Возврат информации о маршруте или ошибку
    
    Работает только с первым сообщением и сообщениями после завершения подагента.
    """

    def __init__(self, llm: GigaChatClient | None = None) -> None:
        """
        Инициализирует маршрутизирующий агент.
        
        Args:
            llm: Клиент LLM (GigaChat). Если не предоставлен, создаёт новый экземпляр.
        """
        self.llm = llm or GigaChatClient()
        self.graph = create_graph(self.llm).compile()

    async def process_user_message(self, user_message: str, state: RouterAgentState | None = None) -> dict:
        """
        Обрабатывает сообщение пользователя и классифицирует его.
        
        Args:
            user_message: Текст сообщения от пользователя
            state: Опциональное состояние (для контекста из предыдущих сообщений)
            
        Returns:
            Dict со словарём результатов классификации:
            - category: Категория (contract, lawsuit, pretrial_claim, simple_question)
            - is_implemented: Реализован ли обработчик
            - routed_to: Куда направлен запрос (contract_agent, simple_question_agent, none)
            - reply: Сообщение для пользователя (если есть ошибка или недоступность)
            - classification_result: Полный результат от LLM
            - error_message: Описание ошибки (если есть)
        """
        if state is None:
            state = RouterAgentState()
        
        state["raw_input"] = user_message

        # Запускаем граф
        result = await self.graph.ainvoke(state)

        return result
