import os
from typing import Any, AsyncIterator

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers.context import collect_runs

from logger import LoggerFactory

from memory import memory_node

from .nodes import answer_node, clear_previous_run_results, clear_before_end
from .state import GeneralQuestionAgentState


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def create_graph(llm) -> StateGraph:
    async def memory_node_wrapper(
        state: GeneralQuestionAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await memory_node(state, llm, config=config)

    async def answer_node_wrapper(
        state: GeneralQuestionAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await answer_node(state, llm, config=config)
    
    async def clear_before_end_wrapper(
        state: GeneralQuestionAgentState,
    ) -> dict[str, Any]:
        return await clear_before_end(state)
    
    async def clear_previous_results_wrapper(
        state: GeneralQuestionAgentState,
    ) -> dict[str, Any]:
        return await clear_previous_run_results(state)

    graph = StateGraph(GeneralQuestionAgentState)

    graph.add_node("clear_previous", clear_previous_results_wrapper)
    graph.add_node("clear_before_end", clear_before_end_wrapper)
    graph.add_node("memory", memory_node_wrapper)
    graph.add_node("answer", answer_node_wrapper)

    graph.add_edge(START, "clear_previous")
    graph.add_edge("clear_previous", "memory")
    graph.add_edge("memory", "answer")
    graph.add_edge("answer", "clear_before_end")
    graph.add_edge("clear_before_end", END)

    return graph


class GeneralQuestionsAgent:
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

    def _build_input_state(self, user_message: str) -> dict:
        return {
            "raw_input": user_message
        }

    def _config(self, thread_id: str) -> dict[str, Any]:
        return {
            "run_name": "GeneralQuestionAgent",
            "configurable": {"thread_id": thread_id},
        }

    @staticmethod
    def _build_metadata(traced_runs, usage: dict[str, Any]) -> dict[str, Any]:
        if not traced_runs:
            return {
                "run_id": "",
                "trace_id": "",
                "latency_ms": 0,
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
            }
        root_run = traced_runs[-1]
        latency_ms = 0
        if root_run.start_time and root_run.end_time:
            latency_ms = int(
                (root_run.end_time - root_run.start_time).total_seconds() * 1000
            )
        return {
            "run_id": str(root_run.id),
            "trace_id": str(root_run.trace_id),
            "latency_ms": latency_ms,
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }

    async def process_user_message(self, user_message: str, thread_id: str) -> dict[str, Any]:
        input_state = self._build_input_state(user_message)

        with collect_runs() as runs_cb:
            response = await self.graph.ainvoke(
                input_state,
                config=self._config(thread_id),
            )
        logger.debug(f"Got response: {response}")
        usage = response.get("usage_metadata", {}) or {}
        result = {
            "response": response,
            "metadata": self._build_metadata(runs_cb.traced_runs, usage),
        }
        logger.debug(f"Got result: {result}")
        return result

    async def astream_user_message(
        self,
        user_message: str,
        thread_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Стриминговая обработка: пропускает чанки ответа LLM из custom-канала
        графа и в конце отдаёт итоговый result со всей метаинформацией.
        """
        input_state = self._build_input_state(user_message)
        config = self._config(thread_id)

        with collect_runs() as runs_cb:
            async for stream_mode, payload in self.graph.astream(
                input_state,
                config=config,
                stream_mode=["custom", "values"],
            ):
                if stream_mode == "custom":
                    yield {"channel": "progress", "data": payload}

        snapshot = await self.graph.aget_state(config)
        final_values: dict[str, Any] = snapshot.values if snapshot else {}
        usage = final_values.get("usage_metadata", {}) or {}
        metadata = self._build_metadata(runs_cb.traced_runs, usage)

        result = {
            "response": final_values,
            "metadata": metadata,
        }
        yield {"channel": "result", "data": result}