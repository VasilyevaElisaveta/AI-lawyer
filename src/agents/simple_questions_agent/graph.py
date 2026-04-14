from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from .nodes import answer_node
from .state import SimpleQuestionAgentState

from ..llm_client import GigaChatClient

from ...memory import memory_node


def create_graph(llm: GigaChatClient) -> StateGraph:
    """
    Создаёт граф агента простых вопросов.
    
    Граф состоит из одного узла:
    1. answer - генерация ответа на вопрос
    
    После генерации ответа граф завершает работу.
    """

    async def memory_node_wrapper(state: SimpleQuestionAgentState) -> dict[str, Any]:
        return await memory_node(state, llm)

    async def answer_node_wrapper(state: SimpleQuestionAgentState) -> dict[str, Any]:
        return await answer_node(state, llm)

    graph = StateGraph(SimpleQuestionAgentState)

    graph.add_node("memory", memory_node_wrapper)
    graph.add_node("answer", answer_node_wrapper)

    # Определяем рёбра
    graph.add_edge(START, "memory")
    graph.add_edge("memory", "answer")
    graph.add_edge("answer", END)

    return graph


class SimpleQuestionAgent:
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

    def _build_input_state(self, user_message: str) -> dict:
        return {
            "raw_input": user_message
        }

    async def process_user_message(self, user_message: str, thread_id: str) -> dict[str, Any]:
        input_state = self._build_input_state(user_message)
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