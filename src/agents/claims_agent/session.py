"""
Сброс полей сессии claims_agent перед новым запуском пайплайна.
"""
from typing import Any


# Поля дела и служебные данные прогона, очищаемые после завершения
_SESSION_FIELD_KEYS: tuple[str, ...] = (
    "current_agent",
    "continue_current_task",
    "raw_input",
    "input_data",
    "plaintiff_info",
    "defendant_info",
    "third_parties_info",
    "court_info",
    "facts",
    "documents",
    "claims",
    "pretrial_settlement",
    "complaint_type",
    "complaint_sphere",
    "complaint_sending_method",
    "complaint_response_deadline",
    "complaint_deadline_basis",
    "principal_amount",
    "penalty_amount",
    "interest_amount",
    "moral_damage",
    "court_expenses",
    "penalty_rate",
    "penalty_start_date",
    "penalty_end_date",
    "interest_start_date",
    "interest_end_date",
    "cbr_key_rate",
    "case_type",
    "case_category",
    "is_property_dispute",
    "classification_data",
    "validation_errors",
    "validation_attempts",
    "is_valid",
    "applicable_laws",
    "legal_positions",
    "state_duty",
    "total_claim",
    "calculation_details",
    "generated_document",
    "qa_passed",
    "qa_feedback",
    "qa_attempts",
    "final_document",
    "document_path",
    "pipeline_status",
    "error",
    "usage_metadata",
)


def session_reset_values() -> dict[str, Any]:
    """Значения для очистки сессии в checkpoint."""
    reset: dict[str, Any] = {key: None for key in _SESSION_FIELD_KEYS}
    reset["validation_errors"] = []
    reset["validation_attempts"] = 0
    reset["qa_attempts"] = 0
    reset["usage_metadata"] = {}
    return reset
