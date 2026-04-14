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

    decision = await chain.ainvoke(input_d)
    d = {
        "contract_class": decision,
    }
    state.update(d)
    return dict(state)


def contract_classification_router(state):
    desicion = state.get("contract_class", "question")
    desicion_node = {
        "generation": "generator_intake",
        "question": "question_intake"
    }.get(desicion)
    return desicion_node