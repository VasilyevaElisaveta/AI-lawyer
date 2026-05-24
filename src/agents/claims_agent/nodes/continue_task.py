import os
from typing import Any

from logger import LoggerFactory
from langchain_core.runnables import RunnableConfig

from ..state import ClaimsAgentState

from ...common.continue_task import check_continue_task


logger = LoggerFactory.get_logger(
    name="ClaimsAgentContinueTaskNode",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

_DOC_LABELS = {
    "lawsuit": "исковое заявление",
    "complaint": "досудебная претензия",
}

_CONTEXT_FIELDS = (
    "document_type",
    "plaintiff_info",
    "defendant_info",
    "facts",
    "claims",
    "court_info",
    "principal_amount",
)


def build_continue_context(state: ClaimsAgentState) -> dict[str, Any]:
    doc_type = state.get("document_type") or "lawsuit"
    doc_label = _DOC_LABELS.get(doc_type, doc_type)
    validation_errors = state.get("validation_errors") or []

    collected = {
        key: state.get(key)
        for key in _CONTEXT_FIELDS
        if state.get(key) not in (None, "", 0, 0.0)
    }

    lines = [
        f"Активная задача: подготовка документа «{doc_label}» (тип: {doc_type}).",
        "Статус: ожидание ввода пользователя для завершения этой задачи.",
    ]
    if validation_errors:
        lines.append("Ассистент просил пользователя указать:")
        lines.extend(f"  • {err}" for err in validation_errors)
    else:
        lines.append(
            "Список недостающих полей в state пуст — ориентируйся на тип документа и текст сообщения."
        )

    return {
        "task_label": f"подготовка: {doc_label}",
        "collected_fields": collected,
        "session_context": "\n".join(lines),
    }


async def evaluate_continue_task(
    raw_input: str,
    session_state: ClaimsAgentState,
    llm,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    if not raw_input.strip():
        return {"continue_current_task": True, "continue_reasoning": "пустое сообщение"}

    ctx = build_continue_context(session_state)
    return await check_continue_task(
        raw_input=raw_input,
        task_label=ctx["task_label"],
        collected_fields=ctx["collected_fields"],
        session_context=ctx["session_context"],
        llm=llm,
        config=config,
    )
