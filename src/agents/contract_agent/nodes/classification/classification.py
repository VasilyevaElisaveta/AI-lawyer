from langchain_core.prompts import ChatPromptTemplate

from .prompts import (
    make_classification_dict,
    CLASSIFICATION_PROMPT, CLASSIFICATION_SYSTEM
)

from .....utils import LoggerFactory


logger = LoggerFactory.get_logger("ContractAgentClassificationNode")


async def contract_classification_node(state, llm):
    logger.info("Start...")
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
    logger.debug(f"Got result decision: {decision}")
    logger.info("Finish")
    return dict(state)


def contract_classification_router(state):
    logger.info("Start router...")
    decision = state.get("contract_class", "question")
    decision_node = {
        "generation": "generator_intake",
        "question": "question_intake"
    }.get(decision)
    logger.debug(f"Selected node: {decision_node}")
    logger.info("Finish router")
    return decision_node