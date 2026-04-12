from typing import Any, Dict

from langchain_core.messages import AIMessage

from ...state import AgentState


async def final_node(state: AgentState) -> Dict[str, Any]:
    """Финальная нода: возврат документа или ответа пользователю."""
    if state.get("response_to_user"):
        final_text = state["response_to_user"]
    else:
        final_text = state.get("generated_document", "")

    state["final_document"] = final_text

    messages = state.get("messages", []) or []
    if final_text:
        messages.append(AIMessage(content=final_text))
    state["messages"] = messages

    return dict(state)
