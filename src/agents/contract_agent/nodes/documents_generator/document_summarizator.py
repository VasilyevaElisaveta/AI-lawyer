import re

from langchain_core.prompts import ChatPromptTemplate

from .prompts import CONTRACT_SUMMARY_SYSTEM, CONTRACT_SUMMARY_PROMPT
from .documents_templates import CONTRACT_TEMPLATES

from ....utils import _normalize_space


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:markdown|md)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


async def contract_summary_node(state, llm):
    contract_type = state.get("contract_type")
    markdown = _normalize_space(state.get("generated_markdown", ""))

    if not contract_type or contract_type not in CONTRACT_TEMPLATES:
        state["validation_errors"] = ["Невозможно сделать суммаризацию: неизвестный contract_type."]
        return state

    if not markdown:
        state["validation_errors"] = ["Невозможно сделать суммаризацию: пустой Markdown."]
        return state

    prompt = ChatPromptTemplate.from_messages([
        ("system", CONTRACT_SUMMARY_SYSTEM),
        ("human", CONTRACT_SUMMARY_PROMPT),
    ])
    chain = prompt | llm

    raw = await chain.ainvoke({
        "contract_type": contract_type,
        "markdown": markdown,
    })

    summary = _strip_code_fence(raw)

    state["document_summary"] = summary
    state["summary_source"] = "generated_markdown"
    state["summary_attempts"] = state.get("summary_attempts", 0) + 1
    state["final_document"] = summary
    state.setdefault("summarized_documents", [])
    state["summarized_documents"] = state["summarized_documents"] + [summary]
    return state