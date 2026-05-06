import os

from libs.logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from .promtps import (
    make_decision_dict, make_answer_dict,
    DECISION_PROMPT, DECISION_SYSTEM, ANSWER_PROMPT, ANSWER_SYSTEM
)

from ....utils import safe_parse_json


logger = LoggerFactory.get_logger(
    name="ContractAgentQuestionAnswererAnswerNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def contract_answer_decision_node(state, llm, config: RunnableConfig | None = None):
    logger.info("Start...")
    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}
    messages_str = state.get("messages_str", "")
    if not messages_str:
        print("messages_str not in state")
    summarized_documents_str = state.get("summarized_documents_str", "")
    if not summarized_documents_str:
        print("summarized_documents_str not in state")

    input_d = make_decision_dict(raw_input, messages_str, summarized_documents_str)
    prompt = ChatPromptTemplate.from_messages([
        ("system", DECISION_SYSTEM),
        ("human", DECISION_PROMPT)
    ])

    chain = prompt | llm

    response = await chain.ainvoke(input_d, config=config)
    raw = response.content
    decision = safe_parse_json(raw)

    d = {
        "decision": decision,
    }
    state.update(d)
    logger.debug(f"Got result decision: {decision}")
    logger.info("Finish")
    return state


def contract_document_answer_decision_router(state):
    logger.info("Start router...")
    decision = state.get("decision", {})
    decision_node = "answer_with_docs" if isinstance(decision, dict) and decision.get("need_documents", False) else "question_answer"
    logger.debug(f"Selected node: {decision_node}")
    logger.info("Finish router")
    return decision_node


async def contract_answer_with_docs_node(state, llm, config: RunnableConfig | None = None):
    logger.info("Start...")
    raw_input = state.get("raw_input", "")
    decision = state.get("decision", {})
    docs = state.get("generated_documents", [])
    if isinstance(decision, dict):
        document_ids = decision.get("document_ids", [-1])
    else:
        document_ids = [-1]

    selected_docs = [
        docs[i] for i in document_ids
        if (i < len(docs)) and (i >= -len(docs))
    ]
    context = "\n\n".join(selected_docs)

    input_d = make_answer_dict(raw_input, context)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ANSWER_SYSTEM),
        ("human", ANSWER_PROMPT)
    ])

    chain = prompt | llm

    response = await chain.ainvoke(input_d, config=config)
    answer = response.content
    messages = state.get("messages", []) or []
    if answer:
        messages.append(AIMessage(content=answer))
    state["messages"] = messages
    d = {
        "response_to_user": answer
    }
    state.update(d)
    logger.debug(f"Got result answer: {answer}")
    logger.info("Finish")
    return state