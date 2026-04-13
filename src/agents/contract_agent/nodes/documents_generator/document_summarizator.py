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

    state.setdefault("summarized_documents", [])
    state["summarized_documents"] = state["summarized_documents"] + [summary]
    return state