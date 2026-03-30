from __future__ import annotations

import re
from typing import Any

from .fields import BOOLEAN_FIELDS, NUMERIC_FIELDS
from .templates import DOCUMENT_TEMPLATES
from .utils import format_amount, render_template
from .state import AgentState


def generate_document(state: AgentState) -> str:
    doc_type = state.get("doc_type", "lawsuit")
    template = DOCUMENT_TEMPLATES.get(doc_type, DOCUMENT_TEMPLATES["lawsuit"])
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
