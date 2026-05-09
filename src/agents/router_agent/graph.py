import os
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers.context import collect_runs

from logger import LoggerFactory

from .nodes import classification_node, clear_previous_run_results, clear_before_end, interrupt_check_node
from .state import RouterAgentState


logger = logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def create_graph(llm) -> StateGraph:
    """
    Создаёт граф маршрутизирующего агента.

    Граф состоит из узлов:
    1. clear_previous - очистка предыдущих результатов
    2. interrupt_check - проверка прерывания активной задачи (если есть)
    3. classification - классификация запроса пользователя в одну из 4 категорий
    4. clear_before_end - очистка перед завершением

    После классификации граф завершает работу, передавая результат маршрутизации.
    """

    async def clear_previous_node_wrapper(
        state: RouterAgentState,
    ) -> dict[str, Any]:
        return await clear_previous_run_results(state)
    
    async def clear_before_end_wrapper(
        state: RouterAgentState,
    ) -> dict[str, Any]:
        return await clear_before_end(state)

    async def interrupt_check_node_wrapper(
        state: RouterAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await interrupt_check_node(state, llm, config=config)

    async def classification_node_wrapper(
        state: RouterAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await classification_node(state, llm, config=config)

    graph = StateGraph(RouterAgentState)

    graph.add_node("clear_previous", clear_previous_node_wrapper)
    graph.add_node("interrupt_check", interrupt_check_node_wrapper)
    graph.add_node("clear_before_end", clear_before_end_wrapper)
    graph.add_node("classification", classification_node_wrapper)

    def route_after_clear(state: RouterAgentState) -> str:
        """Всегда проверяем прерывание - пусть узел решает нужна ли проверка"""
        return "interrupt_check"

    graph.add_edge(START, "clear_previous")
    graph.add_edge("clear_previous", "interrupt_check")
    graph.add_edge("interrupt_check", "classification")
    graph.add_edge("classification", "clear_before_end")
    graph.add_edge("clear_before_end", END)

    return graph


class RouterAgent:
    def __init__(self, llm) -> None:
        self.llm = llm
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