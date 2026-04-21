"""
Агент для генерации исковых заявлений и претензий.
"""
from .graph import ClaimsAgent
from .state import ClaimsAgentState

__all__ = ["ClaimsAgent", "ClaimsAgentState"]