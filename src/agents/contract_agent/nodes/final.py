from typing import Any, Dict

from ..state import AgentState


async def final_node(state: AgentState) -> Dict[str, Any]:
    """Финальная нода: возврат документа."""
    state["final_document"] = state.get("generated_document", "")
    return dict(state)