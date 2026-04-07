from typing import Any, Dict

from ..state import AgentState


async def final_node(state: AgentState) -> Dict[str, Any]:
    """Финальная нода: возврат документа или ответа пользователю."""
    if state.get("response_to_user"):
        state["final_document"] = state["response_to_user"]
    else:
        state["final_document"] = state.get("generated_document", "")
    return dict(state)