from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

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
    def __init__(self, llm: GigaChatClient | None = None) -> None:
        self.llm = llm or GigaChatClient()
        # Временное решение для сохранения состояния между вызовами.
        self.memory = MemorySaver()
        # В проде заменить на RedisSaver или другое долговременное хранилище.
        # from langgraph.checkpoint.redis import RedisSaver
        # self.memory = RedisSaver.from_conn_string(
        #     "redis://localhost:6379",
        #     key_prefix=f"contract_agent:"
        # )
        self.graph = create_graph(self.llm).compile(checkpointer=self.memory)
    
    def _build_input_state(self, raw_input: str) -> dict:
        return {
            "raw_input": raw_input
        }

    async def process_user_message(self, raw_input: str, thread_id: str) -> dict:
        input_state = self._build_input_state(raw_input)
        result = await self.graph.ainvoke(
            input_state,
            config={
                "configurable": {
                    "thread_id": thread_id
                }
            }
        )
        result["handled_by_agent"] = True
        return result