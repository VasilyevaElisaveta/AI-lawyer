import os
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers.context import collect_runs

from logger import LoggerFactory

from .nodes import (
    classification_node,
    clear_previous_run_results,
    clear_before_end,
    continue_task_node,
    field_extraction_node,
)
from .state import RouterAgentState


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def _route_after_clear_previous(
    state: RouterAgentState,
) -> Literal["continue_task_check", "classification"]:
    if state.get("current_agent"):
        return "continue_task_check"
    return "classification"


def _route_after_continue_task(
    state: RouterAgentState,
) -> Literal["classification", "field_extraction"]:
    if state.get("continue_current_task") and state.get("routed_to"):
        return "field_extraction"
    return "classification"


def create_graph(llm) -> StateGraph:
    """
    Граф маршрутизирующего агента:

    1. clear_previous — сброс полей текущего прогона
    2. continue_task_check (если current_agent задан) — продолжать ли текущую задачу
    3. classification — выбор агента (пропускается при продолжении задачи)
    4. field_extraction — извлечение обязательных полей агента
    """

    async def clear_previous_node_wrapper(
        state: RouterAgentState,
    ) -> dict[str, Any]:
        return await clear_previous_run_results(state)

    async def clear_before_end_wrapper(
        state: RouterAgentState,
    ) -> dict[str, Any]:
        return await clear_before_end(state)

    async def continue_task_node_wrapper(
        state: RouterAgentState,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        return await continue_task_node(state, llm, config=config)

    async def classification_node_wrapper(
        state: RouterAgentState,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        return await classification_node(state, llm, config=config)

    async def field_extraction_node_wrapper(
        state: RouterAgentState,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        return await field_extraction_node(state, llm, config=config)

    graph = StateGraph(RouterAgentState)

    graph.add_node("clear_previous", clear_previous_node_wrapper)
    graph.add_node("continue_task_check", continue_task_node_wrapper)
    graph.add_node("classification", classification_node_wrapper)
    graph.add_node("field_extraction", field_extraction_node_wrapper)
    graph.add_node("clear_before_end", clear_before_end_wrapper)

    graph.add_edge(START, "clear_previous")
    graph.add_conditional_edges(
        "clear_previous",
        _route_after_clear_previous,
        {
            "continue_task_check": "continue_task_check",
            "classification": "classification",
        },
    )
    graph.add_conditional_edges(
        "continue_task_check",
        _route_after_continue_task,
        {
            "classification": "classification",
            "field_extraction": "field_extraction",
        },
    )
    graph.add_edge("classification", "field_extraction")
    graph.add_edge("field_extraction", "clear_before_end")
    graph.add_edge("clear_before_end", END)

    return graph


class RouterAgent:
    def __init__(self, llm) -> None:
        self.llm = llm
        self.memory = MemorySaver()
        self.graph = create_graph(self.llm).compile(checkpointer=self.memory)

    def _build_input_state(self, raw_input: str) -> dict:
        return {
            "raw_input": raw_input
        }

    async def clear_current_agent(self, thread_id: str) -> None:
        """Сбрасывает активную задачу после успешного завершения работы агента."""
        await self.graph.aupdate_state(
            config={"configurable": {"thread_id": thread_id}},
            values={
                "current_agent": None,
                "agent_fields": {},
                "category": None,
                "document_type": None,
                "fields_complete": None,
            },
        )
        logger.info("Router current_agent cleared for thread %s", thread_id)

    async def process_user_message(self, raw_input: str, thread_id: str) -> dict:
        input_state = self._build_input_state(raw_input)
        with collect_runs() as runs_cb:
            response = await self.graph.ainvoke(
                input_state,
                config={
                    "run_name": "RouterAgent",
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            )
        root_run = runs_cb.traced_runs[-1]
        logger.debug(f"RESPONSE: {response}")
        usage = response.get("usage_metadata", {})
        result = {
            "response": response,
            "metadata": {
                "run_id": str(root_run.id),
                "trace_id": str(root_run.trace_id),
                "latency_ms": int((root_run.end_time - root_run.start_time).total_seconds() * 1000),
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
            },
        }
        logger.debug(f"Got result: {result}")
        return result
