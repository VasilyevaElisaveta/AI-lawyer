from typing import Annotated, Any, Literal, TypedDict, Optional

from langgraph.graph.message import add_messages


class RouterAgentState(TypedDict, total=False):
    """
    Состояние маршрутизирующего агента.

    total=False → все поля опциональны на уровне TypedDict.
    В коде узлов используем state.get("field", default).
    """

    messages: Annotated[list, add_messages]

    raw_input: Optional[str]

    category: Literal["contract", "claim", "pretrial_claim", "general_question"]
    document_type: Optional[str]
    classification_confidence: float
    classification_result: dict[str, Any]

    is_implemented: bool
    error: Optional[str]

    routed_to: Optional[str]

    usage_metadata: dict[str, Any]
