import os

from logger import LoggerFactory

from ....utils import messages_to_str, documents_to_str


logger = LoggerFactory.get_logger(
    name="ContractAgentQuestionAnswererIntakeNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def _clear_previous_run_results(state):
    state["document_ids"] = []
    state["decision"] = {}
    state["response_to_user"] = None
    state["generated_docx_base64"] = None
    state["response_to_user"] = None
    state["markdown_generation_attempts"] = 0
    state["document_created"] = False
    logger.info("Previous run results cleared")


async def contract_question_intake_node(state):
    """
    Используется в случаях, если агенту по договорам задали какой-либо вопрос, а не дали задание на генерацию документа.
    Собирает и валидирует необходимые поля из state.
    """
    logger.info("Start...")
    _clear_previous_run_results(state)
    messages = state.get("messages", [])
    messages_str = messages_to_str(messages)
    summarized_documents = state.get("summarized_documents", [])
    summarized_documents_str = documents_to_str(summarized_documents)
    d = {
        "messages_str": messages_str,
        "summarized_documents_str": summarized_documents_str
    }
    state.update(d)
    logger.info("Finish")
    return dict(state)