from typing import Any, Dict

from langchain_core.messages import AIMessage

from ...state import ContractAgentState

from .....utils import LoggerFactory


logger = LoggerFactory.get_logger("ContractAgentDocumentGeneratorFinalNode")


def clear_results_before_end(state):
    state["collected_fields"] = {}
    state["contract_type"] = None
    state["doc_type"] = None
    state["current_node"] = None
    logger.info("Clear some results before end")


async def contract_generator_final_node(state: ContractAgentState) -> Dict[str, Any]:
    logger.info("Start...")
    if state.get("response_to_user"):
        final_text = state["response_to_user"]
        logger.debug(f"Get final text: {final_text}")
    elif state.get("generated_docx_base64"):
        final_text = state.get("generated_docx_base64", "")
        logger.debug(f"Get final text: {final_text}")
        clear_results_before_end(state)
    else:
        final_text = "Произошла ошибка при генерации ответа, повторите попытку позже или в другом чате."
        state["response_to_user"] = final_text
        clear_results_before_end(state)

    messages = state.get("messages", []) or []
    if final_text:
        messages.append(AIMessage(content=final_text))
    state["messages"] = messages
    logger.debug(f"Got result message: {final_text}")
    logger.info("Finish")
    return dict(state)
