import json
import re
from typing import Any, Dict, List


def render_template(template: str, variables: Dict[str, Any]) -> str:
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return ""

    return template.format_map(_SafeDict(variables))


def normalize_braces(text: str) -> str:
    return text.replace("{{", "{").replace("}}", "}")


def _normalize_space(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value).strip()


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
    text = normalize_braces(text)
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
    

def messages_to_str(messages) -> str:
    role_map = {
        "human": "User",
        "ai": "Assistant",
        "system": "System"
    }

    formatted_messages = []

    for msg in messages:
        # Handle both dict and BaseMessage objects
        if hasattr(msg, 'type') and hasattr(msg, 'content'):
            # BaseMessage object
            role = role_map.get(msg.type, msg.type)
            content = msg.content.strip()
        elif isinstance(msg, dict):
            # Dict object
            role = role_map.get(msg.get("type", ""), msg.get("type", "unknown"))
            content = msg.get("content", "").strip()
        else:
            # Unknown type
            role = "unknown"
            content = str(msg).strip()

        if not content:
            continue

        formatted_messages.append(f"{role}: {content}")

    return "\n".join(formatted_messages)


def update_tokens_metadata(m1, m2, fields):
    for key in fields:
        if key in m2:
            m2[key] += m1.get(key, 0)
    return m2


def documents_to_str(documents: List[str]) -> str:
    formatted_messages = []
    for i, document in enumerate(documents):
        formatted_messages.append(f"{i}: ")
        formatted_messages.append(document)
    return "\n".join(formatted_messages)


def safe_parse_list_int(output: str) -> List[int]:
    if not output:
        return []
    numbers = re.findall(r'-?\d+', output)
    return [int(n) for n in numbers]