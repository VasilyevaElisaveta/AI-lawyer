from typing import Any, Dict

from ..state import AgentState

from ...utils import find_missing_required_fields


async def validation_node(state: AgentState, field="contract") -> Dict[str, Any]:
    """Нода валидации наличия необходимых полей."""
    validation_attempts = state.get("validation_attempts", 0) + 1
    state["validation_attempts"] = validation_attempts

    missing_fields = find_missing_required_fields(state, field)
    if missing_fields:
        state.update(
            {
                "validation_errors": missing_fields,
                "is_valid": False,
                "validation_attempts": validation_attempts,
            }
        )
        return dict(state)
    validation_attempts = 0
    state.update(
        {
            "validation_errors": [],
            "is_valid": True,
            "validation_attempts": validation_attempts,
        }
    )
    return dict(state)