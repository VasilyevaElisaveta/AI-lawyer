from langchain_core.messages import AIMessage

from .....utils import LoggerFactory

logger = LoggerFactory.get_logger("ContractAgentQuestionAnswererFinalNode")


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