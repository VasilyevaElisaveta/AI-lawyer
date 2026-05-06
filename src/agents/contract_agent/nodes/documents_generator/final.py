import os
from typing import Any, Dict

from libs.logger import LoggerFactory

from langchain_core.messages import AIMessage

from ...state import ContractAgentState


logger = LoggerFactory.get_logger(
    name="ContractAgentDocumentGeneratorFinalNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") is not "DEBUG" else None,
)


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
        state["response_to_user"] = final_text
        state["document_created"] = True
        logger.debug(f"Get final text: {final_text}")
        clear_results_before_end(state)
    else:
        final_text = "Произошла ошибка при генерации ответа, повторите попытку позже или в другом чате."
        state["response_to_user"] = final_text
        clear_results_before_end(state)

    messages = state.get("messages", [])
    markdown_text = state.get("generated_markdown", "")
    if markdown_text:
        messages.append(AIMessage(content=markdown_text))
    state["messages"] = messages
    logger.debug(f"Got base64 result message: {final_text}")
    logger.debug(f"Got markdown result message: {markdown_text}")
    logger.info("Finish")
    return dict(state)
