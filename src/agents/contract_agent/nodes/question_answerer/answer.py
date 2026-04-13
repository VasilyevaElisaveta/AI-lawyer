from langchain_core.prompts import ChatPromptTemplate

from .promtps import (
    make_decision_dict, make_answer_dict, 
    DECISION_PROMPT, DECISION_SYSTEM, ANSWER_PROMPT, ANSWER_SYSTEM
)

from ....utils import safe_parse_json


async def contract_answer_decision_node(state, llm):
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
    prompt = ChatPromptTemplate.from_messages(
        ("system", DECISION_SYSTEM)
        ("human", DECISION_PROMPT)
    )

    chain = prompt | llm

    raw = await chain.ainvoke(input_d)
    decision = safe_parse_json(raw)

    d = {
        "decision": decision,
    }
    state.update(d)
    return state


def contract_document_answer_decision_router(state):
    if state["decision"].get("need_documents", False):
        return "answer_with_docs"
    else:
        return "question_answer"


async def contract_answer_with_docs_node(state, llm):
    raw_input = state.get("raw_input", "")
    decision = state.get("decision", "")
    docs = state.get("generated_documents", [])
    document_ids = decision.get("document_ids", [-1])

    selected_docs = [
        docs[i] for i in document_ids
        if (i < len(docs)) and (i >= -len(docs))
    ]
    context = "\n\n".join(selected_docs)

    input_d = make_answer_dict(raw_input, context)
    prompt = ChatPromptTemplate.from_messages(
        ("system", ANSWER_SYSTEM)
        ("human", ANSWER_PROMPT)
    )

    chain = prompt | llm

    answer = await chain.ainvoke(input_d)

    d = {
        "response_to_user": answer
    }
    state.update(d)
    return state