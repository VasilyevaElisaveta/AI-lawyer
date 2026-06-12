"""
Сбор полей дела: разбор текста пользователя + LLM.
Тип документа (иск/претензия) задаёт router и не перезаписывается intake.
"""
import os
import json
from typing import Any

from logger import LoggerFactory

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from .text_parse import parse_labeled_user_text

from ...state import ClaimsAgentState
from ...prompts import INTAKE_HUMAN, INTAKE_SYSTEM, render_template
from ...utils import coerce_documents_text

from ....utils import extract_llm_json, update_tokens_metadata

logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

_FIELD_MAP: dict[str, str] = {
    "document_type": "document_type",
    "plaintiff_info": "plaintiff_info",
    "defendant_info": "defendant_info",
    "third_parties_info": "third_parties_info",
    "court_info": "court_info",
    "facts": "facts",
    "documents": "documents",
    "claims": "claims",
    "pretrial_settlement": "pretrial_settlement",
    "principal_amount": "principal_amount",
    "penalty_amount": "penalty_amount",
    "interest_amount": "interest_amount",
    "moral_damage": "moral_damage",
    "court_expenses": "court_expenses",
    "penalty_rate": "penalty_rate",
    "penalty_start_date": "penalty_start_date",
    "penalty_end_date": "penalty_end_date",
    "interest_start_date": "interest_start_date",
    "interest_end_date": "interest_end_date",
    "cbr_key_rate": "cbr_key_rate",
    "complaint_type": "complaint_type",
    "complaint_sphere": "complaint_sphere",
    "complaint_sending_method": "complaint_sending_method",
    "complaint_response_deadline": "complaint_response_deadline",
    "complaint_deadline_basis": "complaint_deadline_basis",
}


def intake_node(
    state: ClaimsAgentState,
    llm,
    config: RunnableConfig,
) -> dict[str, Any]:
    doc_type = state.get("document_type", "lawsuit")
    locked = state.get("document_type_locked", False)
    logger.info(
        "[claims][intake] извлечение полей (документ=%s%s)",
        doc_type,
        ", тип задан router" if locked else "",
    )
    input_data: dict | None = state.get("input_data")
    if input_data:
        return _finalize_updates(_map_structured(input_data, skip_document_type=locked), locked, doc_type)
    raw_input: str = state.get("raw_input", "")
    if not raw_input:
        logger.warning("[claims][intake] пустое сообщение")
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}
    return _extract_from_text(raw_input, state, llm, config, locked, doc_type)


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (int, float)):
        return value == 0 or value == 0.0
    return False


def _map_structured(data: dict, *, skip_document_type: bool = False) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for src, dst in _FIELD_MAP.items():
        if skip_document_type and src == "document_type":
            continue
        if src not in data:
            continue
        value = data[src]
        if dst == "documents":
            value = coerce_documents_text(value)
        if _is_empty_value(value):
            continue
        updates[dst] = value
    return updates


def _merge_updates(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        if not _is_empty_value(value):
            merged[key] = value
    return merged


def _finalize_updates(
    updates: dict[str, Any],
    locked: bool,
    doc_type: str,
) -> dict[str, Any]:
    if locked:
        updates.pop("document_type", None)
    elif not updates.get("document_type"):
        updates["document_type"] = doc_type
    if updates:
        logger.info("[claims][intake] извлечено полей: %s", ", ".join(sorted(updates.keys())))
    return updates


def _collect_known_fields(state: ClaimsAgentState) -> dict[str, Any]:
    known: dict[str, Any] = {}
    for dst in _FIELD_MAP.values():
        value = state.get(dst)
        if not _is_empty_value(value):
            known[dst] = value
    return known


def _extract_from_text(
    text: str,
    state: ClaimsAgentState,
    llm,
    config: RunnableConfig,
    locked: bool,
    doc_type: str,
) -> dict[str, Any]:
    updates = _map_structured(parse_labeled_user_text(text), skip_document_type=locked)
    if updates:
        logger.info("[claims][intake] разобран текст без LLM: %s", ", ".join(updates.keys()))
    validation_errors = state.get("validation_errors", [])
    additional = ""
    if validation_errors:
        additional = (
            "\n\nНедостающие данные по прошлой проверке:\n"
            + "\n".join(f"- {e}" for e in validation_errors)
        )
    known = _collect_known_fields(state)
    if known:
        additional += (
            "\n\nУже известные данные:\n"
            + json.dumps(known, ensure_ascii=False, indent=2)
        )
    prompt_text = render_template(
        INTAKE_HUMAN,
        {"user_input": text, "additional_context": additional},
    )
    usage_metadata = state.get("usage_metadata", {}) or {}
    try:
        response = llm.invoke(
            [SystemMessage(content=INTAKE_SYSTEM), HumanMessage(content=prompt_text)],
            config=config,
        )
        usage_metadata = update_tokens_metadata(
            usage_metadata,
            getattr(response, "usage_metadata", {}) or {},
            ["input_tokens", "output_tokens", "total_tokens"],
        )
        data = extract_llm_json(response.content or "")
        if data:
            updates = _merge_updates(updates, _map_structured(data, skip_document_type=locked))
        elif not updates:
            logger.warning("[claims][intake] LLM не вернул JSON, сохранён только текст в facts")
            updates["facts"] = text
    except Exception as e:
        logger.warning("[claims][intake] ошибка LLM (%s), используем уже разобранный текст", e)
        if not updates:
            updates["facts"] = text
    # Если пользователь прислал сырую строку (истец/ответчик/сумма/требования),
    # но не указал отдельный блок фактов — используем весь текст как facts, чтобы
    # не запрашивать то, что уже содержится в сообщении.
    if (
        not _is_empty_value(updates.get("plaintiff_info"))
        or not _is_empty_value(updates.get("defendant_info"))
        or not _is_empty_value(updates.get("claims"))
        or not _is_empty_value(updates.get("principal_amount"))
    ) and _is_empty_value(updates.get("facts")):
        updates["facts"] = text.strip()
    result = _finalize_updates(updates, locked, doc_type)
    result["usage_metadata"] = usage_metadata
    return result
