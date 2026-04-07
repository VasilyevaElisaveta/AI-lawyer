import re
from typing import Any, Dict

from ..state import AgentState
from ..templates import DOCUMENT_TEMPLATES
from ..fields import BOOLEAN_FIELDS, NUMERIC_FIELDS

from ...utils import format_amount, render_template


def generate_document(state: AgentState) -> str:
    doc_type = state.get("doc_type", "contract")
    template = DOCUMENT_TEMPLATES.get(doc_type, DOCUMENT_TEMPLATES["contract"])
    rendered = render_template(
        template,
        {
            key: format_amount(state.get(key, ""))
            if key in NUMERIC_FIELDS + BOOLEAN_FIELDS
            else state.get(key, "")
            for key in set(re.findall(r"\{(.*?)\}", template))
        },
    )
    return re.sub(r"\n{3,}", "\n\n", rendered).strip()


async def generation_node(state: AgentState) -> Dict[str, Any]:
    """Нода для генерации текста документа."""
    document = generate_document(state)
    state["generated_document"] = document
    return dict(state)