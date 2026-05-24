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


def _repair_truncated_json_object(raw: str) -> str:
    """Пытается закрыть обрезанный JSON-объект (частый случай у LLM)."""
    s = raw.strip()
    if not s.startswith("{"):
        return s

    # Убираем оборванное поле в конце: , "key": "val  или  , "
    s = re.sub(r',?\s*"[^"]*"\s*:\s*("[^"]*)?$', "", s)
    s = re.sub(r',?\s*"[^"]*$', "", s)
    s = s.rstrip().rstrip(",")

    open_braces = s.count("{") - s.count("}")
    if open_braces > 0:
        s += "}" * open_braces
    return s


def _try_parse_json_object(raw: str) -> dict[str, Any] | None:
    start = raw.find("{")
    if start == -1:
        return None

    chunk = raw[start:]
    end = chunk.rfind("}")
    candidates: list[str] = []
    if end != -1:
        candidates.append(chunk[: end + 1])
    candidates.append(_repair_truncated_json_object(chunk))

    for attempt in candidates:
        try:
            data = json.loads(attempt)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def extract_llm_json(text: str) -> dict[str, Any]:
    """
    Извлекает JSON-объект из ответа LLM.

    Поддерживает:
    - markdown ```json ... ```
    - обычный { ... }
    - обрезанный JSON без закрывающей }
    - артефакты {{ }} из шаблонов (схлопываются только при наличии двойных скобок)
    """
    if not text or not str(text).strip():
        return {}

    stripped = str(text).strip()
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", stripped, re.DOTALL)
    candidates = [fence.group(1).strip()] if fence else []
    candidates.append(stripped)

    for candidate in candidates:
        parsed = _try_parse_json_object(candidate)
        if parsed:
            return parsed
        if "{{" in candidate or "}}" in candidate:
            parsed = _try_parse_json_object(normalize_braces(candidate))
            if parsed:
                return parsed

    return {}


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
    return extract_llm_json(text)
    

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


def normalize_usage_dict(usage: dict[str, Any] | None) -> dict[str, int]:
    usage = usage or {}
    inp = int(usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or 0)
    out = int(usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or 0)
    total = int(usage.get("total_tokens", 0) or 0)
    if total == 0 and (inp or out):
        total = inp + out
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": total}


def update_tokens_metadata(m1, m2, fields=None):
    del fields
    a = normalize_usage_dict(m1)
    b = normalize_usage_dict(m2)
    return {
        "input_tokens": a["input_tokens"] + b["input_tokens"],
        "output_tokens": a["output_tokens"] + b["output_tokens"],
        "total_tokens": a["total_tokens"] + b["total_tokens"],
    }


def documents_to_str(documents: List[str]) -> str:
    formatted_messages = []
    for i, document in enumerate(documents):
        formatted_messages.append(f"{i}: ")
        formatted_messages.append(document)
    return "\n".join(formatted_messages)


def state_int(state: dict, key: str, default: int = 0) -> int:
    """Число из state: ключ может отсутствовать или быть None после сброса сессии."""
    value = state.get(key, default)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def aggregate_traced_runs_usage(traced_runs) -> dict[str, int]:
    """Суммирует usage_metadata по всем run'ам LangSmith/LangChain в прогоне."""
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for run in traced_runs or []:
        usage = getattr(run, "usage_metadata", None) or {}
        if not isinstance(usage, dict):
            continue
        for key in totals:
            totals[key] += int(usage.get(key, 0) or 0)
    return totals


def merge_usage_dicts(*parts: dict[str, Any]) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for part in parts:
        if not part:
            continue
        for key in totals:
            totals[key] += int(part.get(key, 0) or 0)
    return totals


def usage_from_traced_runs(traced_runs) -> dict[str, int]:
    if not traced_runs:
        return normalize_usage_dict(None)
    root = traced_runs[-1]
    usage = normalize_usage_dict(getattr(root, "usage_metadata", None) or {})
    if usage["total_tokens"] > 0 or usage["input_tokens"] > 0:
        return usage
    return aggregate_traced_runs_usage(traced_runs)


def resolve_run_usage(
    state_usage: dict[str, Any] | None,
    traced_runs,
) -> dict[str, int]:
    """Токены текущего HTTP-запроса: state (GigaChat) с fallback на tracer."""
    usage = normalize_usage_dict(state_usage)
    if usage["total_tokens"] > 0 or usage["input_tokens"] > 0:
        return usage
    return usage_from_traced_runs(traced_runs)


def state_float(state: dict, key: str, default: float = 0.0) -> float:
    value = state.get(key, default)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_parse_list_int(output: str) -> List[int]:
    if not output:
        return []
    numbers = re.findall(r'-?\d+', output)
    return [int(n) for n in numbers]