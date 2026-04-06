from __future__ import annotations

from functools import partial
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from .nodes import (
    intake_node, 
    validation_node, 
    generation_node, 
    qa_node,
    final_node
)
from .llm_client import GigaChatClient
from .state import AgentState


def create_graph(llm: GigaChatClient) -> StateGraph:
    """Создаёт граф агента."""
    graph = StateGraph(AgentState)

    # Добавляем ноды
    graph.add_node("intake", partial(intake_node, llm=llm))
    graph.add_node("validation", validation_node)
    graph.add_node("generation", generation_node)
    graph.add_node("qa", partial(qa_node, llm=llm))
    graph.add_node("final", final_node)

    # Определяем рёбра
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "validation")

    # Conditional от validation
    def validation_router(state: AgentState) -> Literal["intake", "generation", "final"]:
        if state.get("is_valid", False):
            return "generation"
        if state.get("validation_attempts", 0) >= 3:
            return "final"
        return "intake"  # обратно к intake для дозаполнения

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
        self.graph = create_graph(self.llm).compile()

    async def process_user_message(self, user_message: str, state: AgentState | None = None) -> dict[str, Any]:
        if state is None:
            state = AgentState()
        state["raw_input"] = user_message

        # Запускаем граф
        result = await self.graph.ainvoke(state)
        return result