from functools import partial

from langgraph.graph import END, START, StateGraph

from .nodes import answer_node
from .state import SimpleQuestionAgentState

from ..llm_client import GigaChatClient


def create_graph(llm: GigaChatClient) -> StateGraph:
    """
    Создаёт граф агента простых вопросов.
    
    Граф состоит из одного узла:
    1. answer - генерация ответа на вопрос
    
    После генерации ответа граф завершает работу.
    """
    graph = StateGraph(SimpleQuestionAgentState)

    # Добавляем узел ответа
    graph.add_node("answer", partial(answer_node, llm=llm))

    # Определяем рёбра
    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)

    return graph


class SimpleQuestionAgent:
    """
    Агент для ответов на простые вопросы на основе LanggGraph.
    
    Ответственен за:
    1. Получение вопроса пользователя
    2. Генерацию ответа с помощью LLM
    3. Возврат ответа пользователю
    """

    def __init__(self, llm: GigaChatClient | None = None) -> None:
        """
        Инициализирует агента простых вопросов.
        
        Args:
            llm: Клиент LLM (GigaChat). Если не предоставлен, создаёт новый экземпляр.
        """
        self.llm = llm or GigaChatClient()
        self.graph = create_graph(self.llm).compile()

    async def answer_question(self, question: str, state: SimpleQuestionAgentState | None = None) -> str:
        """
        Генерирует ответ на вопрос пользователя.
        
        Args:
            question: Вопрос пользователя
            state: Опциональное состояние (для контекста из предыдущих сообщений)
            
        Returns:
            Строка с ответом на вопрос
        """
        if state is None:
            state = SimpleQuestionAgentState()
        
        state["raw_input"] = question

        # Запускаем граф
        result = await self.graph.ainvoke(state)

        return result.get("reply", "")

    async def process_user_message(self, user_message: str, state: SimpleQuestionAgentState | None = None) -> dict:
        """
        Обрабатывает сообщение пользователя (альтернативное имя для совместимости).
        
        Args:
            user_message: Сообщение пользователя
            state: Опциональное состояние
            
        Returns:
            Dict с результатами обработки:
            - reply: Ответ пользователю
            - handled_by_agent: Всегда True (для совместимости)
        """
        if state is None:
            state = SimpleQuestionAgentState()
        
        state["raw_input"] = user_message

        # Запускаем граф
        result = await self.graph.ainvoke(state)

        return {
            "reply": result.get("reply", ""),
            "handled_by_agent": True,
        }
