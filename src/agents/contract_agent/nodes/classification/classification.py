import os

from logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from .prompts import (
    make_classification_dict,
    CLASSIFICATION_PROMPT, CLASSIFICATION_SYSTEM
)

from ....utils import messages_to_str


logger = LoggerFactory.get_logger(
    name="ContractAgentClassificationNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def contract_classification_node(
    state, 
    llm, 
    config: RunnableConfig | None = None
):
    logger.info("Start...")
    raw_input = state.get("raw_input", "")
    messages = state.get("messages", []) or []
    messages_str = messages_to_str(messages)
    conversation_summary = state.get("conversation_summary", "")

    input_d = make_classification_dict(raw_input, messages_str, conversation_summary)
    prompt = ChatPromptTemplate.from_messages([
        ("system", CLASSIFICATION_SYSTEM),
        ("human", CLASSIFICATION_PROMPT)
    ])

    chain = prompt | llm

    response = await chain.ainvoke(input_d, config=config)
    decision = response.content
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