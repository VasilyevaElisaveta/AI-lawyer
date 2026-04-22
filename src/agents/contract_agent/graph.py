from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

from .nodes import *
from .state import ContractAgentState

from ...memory import memory_node


def create_graph(llm, generator_llm=None) -> StateGraph:
    """Создаёт граф агента."""

    # Создаём wrapper функции для узлов с LLM
    async def summarization_node_wrapper(
        state: ContractAgentState,
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await memory_node(state, llm, config=config)

    async def classification_node_wrapper(
        state: ContractAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await contract_classification_node(state, llm, config=config)

    async def generator_intake_node_wrapper(
        state: ContractAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await contract_generator_intake_node(state, llm, config=config)
    
    async def generator_intake_validation_node_wrapper(state: ContractAgentState,) -> dict[str, Any]:
        return await contract_generator_intake_validation_node(state)

    async def markdown_generation_node_wrapper(
        state: ContractAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await contract_markdown_generation_node(
            state, 
            llm=llm if generator_llm is None else generator_llm, 
            config=config
        )

    async def document_summary_node_wrapper(
        state: ContractAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await contract_document_summary_node(state, llm, config=config)

    async def answer_decision_node_wrapper(
        state: ContractAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await contract_answer_decision_node(state, llm, config=config)

    async def answer_with_docs_node_wrapper(
        state: ContractAgentState, 
        config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        return await contract_answer_with_docs_node(state, llm, config=config)

    async def question_answer_node_wrapper(state: ContractAgentState) -> dict[str, Any]:
        return await contract_question_answer_node(state)

    graph = StateGraph(ContractAgentState)

    graph.add_node("summarization", summarization_node_wrapper)
    graph.add_node("classification", classification_node_wrapper)
    graph.add_node("generator_intake", generator_intake_node_wrapper)
    graph.add_node("generator_intake_validation", generator_intake_validation_node_wrapper)
    graph.add_node("markdown_generation", markdown_generation_node_wrapper)
    graph.add_node("markdown_validation", contract_markdown_validation_node)
    graph.add_node("docx_generation", contract_docx_generation_node)
    graph.add_node("document_summary", document_summary_node_wrapper)
    graph.add_node("generator_final", contract_generator_final_node)

    graph.add_node("question_intake", contract_question_intake_node)
    graph.add_node("answer_decision", answer_decision_node_wrapper)
    graph.add_node("answer_with_docs", answer_with_docs_node_wrapper)
    graph.add_node("question_answer", question_answer_node_wrapper)

    graph.add_edge(START, "summarization")
    graph.add_edge("summarization", "classification")
    graph.add_conditional_edges("classification", contract_classification_router)

    graph.add_edge("generator_intake", "generator_intake_validation")
    graph.add_conditional_edges("generator_intake_validation", contract_generator_validation_router)
    graph.add_edge("markdown_generation", "markdown_validation")
    graph.add_conditional_edges("markdown_validation", contract_markdown_validation_router)
    graph.add_edge("docx_generation", "document_summary")
    graph.add_edge("document_summary", "generator_final")
    graph.add_edge("generator_final", END)

    graph.add_edge("question_intake", "answer_decision")
    graph.add_conditional_edges("answer_decision", contract_document_answer_decision_router)
    graph.add_edge("answer_with_docs", END)
    graph.add_edge("question_answer", END)
    return graph


class ContractAgent:
    def __init__(self, llm, generator_llm=None) -> None:
        self.llm = llm
        self.generator_llm = generator_llm
        # Временное решение для сохранения состояния между вызовами.
        self.memory = MemorySaver()
        # В проде заменить на RedisSaver или другое долговременное хранилище.
        # from langgraph.checkpoint.redis import RedisSaver
        # self.memory = RedisSaver.from_conn_string(
        #     "redis://localhost:6379",
        #     key_prefix=f"contract_agent:"
        # )
        self.graph = create_graph(
            self.llm, 
            generator_llm=generator_llm
        ).compile(checkpointer=self.memory)

    def _build_input_state(self, user_message: str) -> dict:
        return {
            "raw_input": user_message
        }

    async def process_user_message(self, user_message: str, thread_id: str) -> dict[str, Any]:
        input_state = self._build_input_state(user_message)
        result = await self.graph.ainvoke(
            input_state,
            config={
                "run_name": "ContractAgent",
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
        result["document_created"] = bool(result.get("document_created"))
        return result