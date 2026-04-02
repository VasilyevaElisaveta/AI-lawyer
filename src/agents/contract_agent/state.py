from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> "AgentState":
        self.data[key] = value
        return self

    def update(self, **kwargs: Any) -> "AgentState":
        self.data.update(kwargs)
        return self

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)

    def copy(self) -> "AgentState":
        return AgentState(dict(self.data))
