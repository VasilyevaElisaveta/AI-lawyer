from __future__ import annotations

from functools import partial
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from .extraction import build_missing_fields_prompt, find_missing_required_fields, intake_node
from .llm_client import GigaChatClient
from .qa import qa_node
from .state import AgentState
from .document import generate_document


async def validation_node(state: AgentState) -> dict[str, Any]:
    """Нода валидации наличия необходимых полей."""
    validation_attempts = state.get("validation_attempts", 0) + 1
    state["validation_attempts"] = validation_attempts

    missing_fields = find_missing_required_fields(state)
    if missing_fields:
        # Генерируем стандартный ответ с требованием заполнить поля
        prompt = build_missing_fields_prompt(missing_fields)
        state.update(
            {
                "validation_errors": missing_fields,
                "is_valid": False,
                "validation_attempts": validation_attempts,
            }
        )
        return dict(state)
    state.update(
        {
            "validation_errors": [],
            "is_valid": True,
            "validation_attempts": validation_attempts,
        }
    )
    return dict(state)


async def generation_node(state: AgentState) -> dict[str, Any]:
    """Нода для генерации текста документа."""
    document = generate_document(state)
    state["generated_document"] = document
    return dict(state)


async def final_node(state: AgentState) -> dict[str, Any]:
    """Финальная нода: возврат документа."""
    state["final_document"] = state.get("generated_document", "")
    return dict(state)


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