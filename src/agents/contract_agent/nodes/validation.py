from typing import Any, Dict

from ..state import AgentState
from ..fields import FIELD_LABELS

from ...utils import find_missing_required_fields


async def validation_node(state: AgentState, field="contract") -> Dict[str, Any]:
    """Нода валидации наличия необходимых полей."""
    missing_fields = find_missing_required_fields(state, field)
    if missing_fields:
        # Формируем сообщение пользователю с запросом недостающих полей
        missing_labels = [FIELD_LABELS.get(field, field) for field in missing_fields]
        response_message = (
            "Для формирования договора необходимы следующие данные:\n" +
            "\n".join(f"- {label}" for label in missing_labels) +
            "\n\nПожалуйста, предоставьте эту информацию."
        )
        state.update({
            "validation_errors": missing_fields,
            "is_valid": False,
            "response_to_user": response_message,
        })
        return dict(state)
    
    # Все поля заполнены
    state.update({
        "validation_errors": [],
        "is_valid": True,
        "response_to_user": None,
    })
    return dict(state)