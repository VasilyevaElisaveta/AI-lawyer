from langchain_core.prompts import ChatPromptTemplate

from .prompts import (
    make_classification_dict,
    CLASSIFICATION_PROMPT, CLASSIFICATION_SYSTEM
)


async def contract_classification_node(state, llm):
    raw_input = state.get("raw_input", "")

    input_d = make_classification_dict(raw_input)
    prompt = ChatPromptTemplate.from_messages(
        ("system", CLASSIFICATION_SYSTEM)
        ("human", CLASSIFICATION_PROMPT)
    )

    chain = prompt | llm

    desicion = await chain.ainvoke()
    d = {
        "contract_class": desicion,
    }
    state.update(d)
    return dict(state)


def route_contract_class(state):
    return state.get("contract_class", "question")