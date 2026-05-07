import os

from logger import LoggerFactory

from langchain_core.messages import AIMessage


logger = LoggerFactory.get_logger(
    name="ContractAgentQuestionAnswererFinalNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


async def contract_question_answer_node(state):
    logger.info("Start...")
    d = {
        "response_to_user": state["decision"].get("answer", "")
    }
    answer = state["decision"].get("answer", "")
    messages = state.get("messages", []) or []
    if answer:
        messages.append(AIMessage(content=answer))
    state["messages"] = messages
    state.update(d)
    logger.debug(f"Got result response to user: {d["response_to_user"]}")
    logger.info("Finish")
    return dict(state)