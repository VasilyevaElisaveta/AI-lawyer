import os
from typing import Any

from logger import LoggerFactory

from langgraph.graph import END, START, StateGraph
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers.context import collect_runs

from .nodes import classification_node, clear_previous_run_results, clear_before_end
from .state import RouterAgentState

from ..common.checkpointer import (
    create_checkpointer,
    graph_checkpoint_config,
    setup_checkpointer,
)
from ..utils import resolve_run_usage


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def create_graph(llm) -> StateGraph:
    """
    Граф маршрутизирующего агента:
    clear_previous → classification → clear_before_end
    """

    async def clear_previous_node_wrapper(
        state: RouterAgentState,
    ) -> dict[str, Any]:
        return await clear_previous_run_results(state)

    async def clear_before_end_wrapper(
        state: RouterAgentState,
    ) -> dict[str, Any]:
        return await clear_before_end(state)

    async def classification_node_wrapper(
        state: RouterAgentState,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        return await classification_node(state, llm, config=config)

    graph = StateGraph(RouterAgentState)

    graph.add_node("clear_previous", clear_previous_node_wrapper)
    graph.add_node("clear_before_end", clear_before_end_wrapper)
    graph.add_node("classification", classification_node_wrapper)

    graph.add_edge(START, "clear_previous")
    graph.add_edge("clear_previous", "classification")
    graph.add_edge("classification", "clear_before_end")
    graph.add_edge("clear_before_end", END)

    return graph


class RouterAgent:
    def __init__(self, llm) -> None:
        self.llm = llm
        self.memory = create_checkpointer("router")
        self.graph = create_graph(self.llm).compile(checkpointer=self.memory)

    async def initialize_checkpointer(self) -> None:
        await setup_checkpointer(self.memory)

    def _build_input_state(self, raw_input: str) -> dict:
        return {
            "raw_input": raw_input
        }

    async def process_user_message(self, raw_input: str, thread_id: str) -> dict:
        input_state = self._build_input_state(raw_input)
        config = graph_checkpoint_config("router", thread_id)
        config["run_name"] = "RouterAgent"
        with collect_runs() as runs_cb:
            response = await self.graph.ainvoke(
                input_state,
                config=config,
            )
        root_run = runs_cb.traced_runs[-1]
        logger.debug(f"RESPONSE: {response}")
        usage = resolve_run_usage(response.get("usage_metadata"), runs_cb.traced_runs)
        result = {
            "response": response,
            "metadata": {
                "run_id": str(root_run.id),
                "trace_id": str(root_run.trace_id),
                "latency_ms": int((root_run.end_time - root_run.start_time).total_seconds() * 1000),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
            },
        }
        logger.debug(f"Got result: {result}")
        return result
