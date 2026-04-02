from __future__ import annotations

import json
import re
from typing import Any


def render_template(template: str, variables: dict[str, Any]) -> str:
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return ""

    return template.format_map(_SafeDict(variables))


def format_amount(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "Да" if value else "Нет"

    try:
        if isinstance(value, str):
            value = float(value.replace(",", ".")) if re.search(r"\d", value) else value
        if isinstance(value, (int, float)):
            if float(value).is_integer():
                return f"{int(value):,}".replace(",", " ")
            return f"{value:,.2f}".replace(",", " ")
    except ValueError:
        return str(value)

    return str(value)


def build_qa_context(state: dict[str, Any]) -> str:
    data = {k: v for k, v in state.items() if v is not None and v != ""}
    return json.dumps(data, ensure_ascii=False, indent=2)


def parse_json(text: str) -> dict[str, Any]:
    payload = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", payload, re.DOTALL)
    if match:
        payload = match.group(1).strip()

    start = payload.find("{")
    end = payload.rfind("}")
    if start != -1 and end != -1:
        payload = payload[start:end + 1]

    return json.loads(payload)
