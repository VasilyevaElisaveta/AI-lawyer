import os
import re

from logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from .prompts import CONTRACT_SUMMARY_SYSTEM, CONTRACT_SUMMARY_PROMPT

from ....utils import _normalize_space


logger = LoggerFactory.get_logger(
    name="ContractAgentDocumentGeneratorSummarizatorNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:markdown|md)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


async def contract_document_summary_node(state, llm, config: RunnableConfig | None = None):
    logger.info("Start...")
    contract_type = state.get("contract_type")
    markdown = _normalize_space(state.get("generated_markdown", ""))

    prompt = ChatPromptTemplate.from_messages([
        ("system", CONTRACT_SUMMARY_SYSTEM),
        ("human", CONTRACT_SUMMARY_PROMPT),
    ])
    chain = prompt | llm

    response = await chain.ainvoke({
        "contract_type": contract_type,
        "markdown": markdown,
    },
    config=config
    )
    raw = response.content

    summary = _strip_code_fence(raw)

    state.setdefault("summarized_documents", [])
    state["summarized_documents"] = state["summarized_documents"] + [summary]
    logger.debug(f"Got result: summraized document: {summary}")
    logger.info("Finish")
    return state