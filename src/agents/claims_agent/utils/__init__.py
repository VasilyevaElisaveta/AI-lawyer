from typing import Any


def coerce_documents_text(value: Any) -> str:
    """Приводит поле documents к строке (LLM/intake иногда возвращает list)."""
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "; ".join(parts)
    if isinstance(value, str):
        return value
    return str(value).strip()
