from functools import partial
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from .nodes import (
    intake_node, 
    validation_node, 
    generation_node, 
    qa_node,
    final_node
)
from .state import AgentState

from ..llm_client import GigaChatClient
from src.memory.memory_node import memory_node


def create_graph(llm: GigaChatClient) -> StateGraph:
    """Создаёт граф агента."""
    graph = StateGraph(AgentState)

    # Добавляем ноды
    graph.add_node("memory", partial(memory_node, llm=llm))
    graph.add_node("intake", partial(intake_node, llm=llm))
    graph.add_node("validation", validation_node)
    graph.add_node("generation", generation_node)
    graph.add_node("qa", partial(qa_node, llm=llm))
    graph.add_node("final", final_node)

    # Определяем рёбра
    graph.add_edge(START, "memory")
    graph.add_edge("memory", "intake")
    graph.add_edge("intake", "validation")

    # Conditional от validation
    def validation_router(state: AgentState) -> Literal["generation", "final"]:
        if state.get("is_valid", False):
            return "generation"
        return "final"

    graph.add_conditional_edges("validation", validation_router)

    graph.add_edge("generation", "qa")

    # Conditional от qa
    def qa_router(state: AgentState) -> Literal["generation", "final"]:
        qa_attempts = state.get("qa_attempts", 0)
        if qa_attempts >= 3 or state.get("qa_passed", False):
            return "final"
        return "generation"  # перегенерация

    graph.add_conditional_edges("qa", qa_router)

    graph.add_edge("final", END)

    return graph


class ContractAgent:
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
        if result.get("response_to_user"):
            result["reply"] = result["response_to_user"]
        else:
            result["reply"] = result.get("final_document", "")
        result["handled_by_agent"] = True
        result["document_created"] = bool(result.get("generated_document"))
        return result