import json
import re
from typing import Any, Dict, List

from .fields import REQUIRED_FIELDS_BY_TYPE


def render_template(template: str, variables: Dict[str, Any]) -> str:
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
    data = {}
    for k, v in state.items():
        if v is None or v == "":
            continue
        if k == "messages":
            # Конвертируем сообщения в строки для JSON
            data[k] = [f"{msg.type}: {msg.content}" for msg in v]
        else:
            data[k] = v
    return json.dumps(data, ensure_ascii=False, indent=2)


def find_missing_required_fields(state: Dict[str, Any], field_name: str) -> list[str]:
    required = REQUIRED_FIELDS_BY_TYPE.get(field_name, [])
    missing: list[str] = []
    for key in required:
        value = state.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)
    return missing


def _parse_json(text: str) -> dict:
    """Извлекает JSON из ответа LLM (может быть обёрнут в markdown)."""
    # Пробуем ```json ... ```
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Пробуем найти { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"JSON not found in LLM response (first 300 chars): {text[:300]}")


def safe_parse_json(text: str) -> dict[str, Any]:
    try:
        return _parse_json(text)
    except Exception:
        simple_match = re.search(r"\{.*\}", text, re.DOTALL)
        if simple_match:
            try:
                return json.loads(simple_match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}
    

def messages_to_str(messages: List[Dict]) -> str:
    role_map = {
        "human": "User",
        "ai": "Assistant",
        "system": "System"
    }

    formatted_messages = []

    for msg in messages:
        role = role_map.get(msg.get("type", ""), msg.get("type", "unknown"))
        content = msg.get("content", "").strip()

        if not content:
            continue

        formatted_messages.append(f"{role}: {content}")

    return "\n".join(formatted_messages)