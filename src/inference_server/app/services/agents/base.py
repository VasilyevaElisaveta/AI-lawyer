from typing import Any


class BaseGraphAgent:
    async def run(self, message: str, thread_id: str) -> dict[str, Any]:
        raise NotImplementedError