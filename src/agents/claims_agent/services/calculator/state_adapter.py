"""
Связка ClaimsAgentState → CourtDutyCalculator.
"""
from __future__ import annotations

from typing import Any

from .enums import ApplicantType, ClaimType, CourtType, ExemptionType
from .fee_calculator import CourtDutyCalculator, DutyResult

_CONSUMER_CATEGORIES = frozenset({
    "consumer_goods", "consumer_services", "financial_services", "consumer",
})
_LABOR_CATEGORIES = frozenset({
    "dismissal", "salary", "discrimination", "labor_other", "employment",
})

_LEGACY_CATEGORY_TO_CLAIM: dict[str, ClaimType] = {
    "divorce": ClaimType.DIVORCE,
    "alimony": ClaimType.ALIMONY,
    "alimony_children_and_plaintiff": ClaimType.ALIMONY,
    "bankruptcy": ClaimType.BANKRUPTCY,
    "bankruptcy_debtor": ClaimType.BANKRUPTCY,
    "appeal": ClaimType.APPEAL,
    "appeal_appeal": ClaimType.APPEAL,
    "cassation": ClaimType.CASSATION,
    "appeal_cassation": ClaimType.CASSATION,
    "supreme": ClaimType.SUPREME_CASSATION,
    "appeal_supreme": ClaimType.SUPREME_CASSATION,
    "admin_normative": ClaimType.ADMIN_NORMATIVE,
    "admin_non_normative": ClaimType.ADMIN_NON_NORMATIVE,
    "admin_ip_normative": ClaimType.IP_NORMATIVE,
    "admin_compensation": ClaimType.COMPENSATION_DELAY,
    "admin_detention": ClaimType.COMPENSATION_DETENTION,
    "special_proceedings": ClaimType.SPECIAL_PROCEEDING,
    "legal_facts": ClaimType.FACT_ESTABLISHMENT,
    "succession": ClaimType.SUCCESSION,
    "duplicate_writ": ClaimType.DUPLICATE_WRIT,
    "postponement": ClaimType.EXECUTION_ISSUES,
    "review_new": ClaimType.REVIEW_NEW_CIRCUMSTANCES,
    "security": ClaimType.INTERIM_MEASURES,
}


def calculate_state_duty_from_state(state: dict[str, Any]) -> DutyResult:
    """Рассчитать госпошлину по полям состояния агента."""
    classification = state.get("classification_data") or {}
    claim_nature = classification.get("claim_nature")
    if claim_nature is None:
        claim_nature = "property" if state.get("is_property_dispute") else "non_property"

    if claim_nature == "mixed":
        return _calculate_mixed_duty(state, classification)

    claim_type = _resolve_claim_type(
        state,
        classification,
        claim_nature,
        _resolve_court_type(state, classification),
    )
    if claim_type == ClaimType.PROPERTY and _resolve_claim_amount(state) <= 0:
        raise ValueError("Для имущественного спора не указана сумма иска")

    calc = _build_calculator(state, classification, claim_nature)
    return calc.calculate()


def _calculate_mixed_duty(
    state: dict[str, Any],
    classification: dict[str, Any],
) -> DutyResult:
    """Смешанные требования: пошлина за имущественную и неимущественную части (ст. 333.20 НК РФ)."""
    prop = _build_calculator(state, classification, "property").calculate()
    non_prop = _build_calculator(state, classification, "non_property").calculate()
    amount = round(prop.amount + non_prop.amount, 2)
    details = (
        "Смешанные требования (ст. 333.20 НК РФ) — пошлина за каждую часть:\n\n"
        "Имущественная часть:\n"
        f"{prop.calculation_details}\n\n"
        "Неимущественная часть:\n"
        f"{non_prop.calculation_details}\n\n"
        f"Итого к уплате: {amount:,.2f} ₽".replace(",", " ")
    )
    warnings = list(prop.warnings) + list(non_prop.warnings)
    warnings.append(
        "Смешанные требования: госпошлина уплачивается отдельно "
        "за имущественную и неимущественную части."
    )
    return DutyResult(
        amount=amount,
        base_amount=round(prop.base_amount + non_prop.base_amount, 2),
        is_exempt=False,
        exemption_details="",
        calculation_details=details,
        warnings=warnings,
    )


def _build_calculator(
    state: dict[str, Any],
    classification: dict[str, Any],
    claim_nature: str,
) -> CourtDutyCalculator:
    court_type = _resolve_court_type(state, classification)
    claim_type = _resolve_claim_type(state, classification, claim_nature, court_type)
    applicant_type = _resolve_applicant_type(classification)
    claim_amount = _resolve_claim_amount(state)
    exemption = _resolve_exemption(state, classification)
    both_alimony = _resolve_both_alimony(state)
    is_debtor_bankruptcy = _resolve_debtor_bankruptcy(state)

    consumer_amount = claim_amount if exemption == ExemptionType.CONSUMER_PROTECTION else None

    return CourtDutyCalculator(
        court_type=court_type,
        claim_type=claim_type,
        applicant_type=applicant_type,
        claim_amount=claim_amount,
        exemption=exemption,
        consumer_claim_amount=consumer_amount,
        both_alimony=both_alimony,
        is_debtor_bankruptcy=is_debtor_bankruptcy,
    )


def _resolve_court_type(state: dict[str, Any], classification: dict[str, Any]) -> CourtType:
    case_type = (state.get("case_type") or "").lower()
    jurisdiction = (classification.get("court_jurisdiction") or "").lower()

    if case_type == "arbitration" or jurisdiction == "arbitration":
        return CourtType.ARBITRATION
    return CourtType.GENERAL


def _resolve_applicant_type(classification: dict[str, Any]) -> ApplicantType:
    plaintiff = (classification.get("plaintiff_type") or "individual").lower()
    if plaintiff in ("legal_entity", "ip", "state"):
        return ApplicantType.ORGANIZATION
    return ApplicantType.INDIVIDUAL


def _resolve_claim_type(
    state: dict[str, Any],
    classification: dict[str, Any],
    claim_nature: str,
    court_type: CourtType,
) -> ClaimType:
    raw_category = (state.get("case_category") or "").lower()
    category = (classification.get("case_category") or raw_category).lower()
    proceeding = (classification.get("proceeding_type") or "lawsuit").lower()

    if raw_category in _LEGACY_CATEGORY_TO_CLAIM:
        return _LEGACY_CATEGORY_TO_CLAIM[raw_category]
    if category in _LEGACY_CATEGORY_TO_CLAIM:
        return _LEGACY_CATEGORY_TO_CLAIM[category]

    if proceeding == "writ":
        return ClaimType.COURT_ORDER

    if category == "bankruptcy" or raw_category == "bankruptcy":
        return ClaimType.BANKRUPTCY

    if category == "family" or raw_category == "family":
        text = f"{state.get('claims', '')} {state.get('facts', '')}".lower()
        # Денежные требования (в т.ч. после развода) — имущественный иск, не «развод»
        if claim_nature == "property" and _resolve_claim_amount(state) > 0:
            return ClaimType.PROPERTY
        if "алимент" in text:
            return ClaimType.ALIMONY
        if "развод" in text or "расторжен" in text:
            return ClaimType.DIVORCE

    if proceeding == "special":
        if court_type == CourtType.ARBITRATION:
            return ClaimType.FACT_ESTABLISHMENT
        return ClaimType.SPECIAL_PROCEEDING

    if claim_nature == "non_property":
        return ClaimType.NON_PROPERTY
    return ClaimType.PROPERTY


def _resolve_exemption(
    state: dict[str, Any],
    classification: dict[str, Any],
) -> ExemptionType:
    category = (
        classification.get("case_category")
        or state.get("case_category")
        or ""
    ).lower()
    plaintiff = (classification.get("plaintiff_type") or "individual").lower()
    raw_category = (state.get("case_category") or "").lower()

    if raw_category == "bankruptcy_debtor":
        return ExemptionType.BANKRUPTCY_DEBTOR

    if category in _CONSUMER_CATEGORIES and plaintiff == "individual":
        return ExemptionType.CONSUMER_PROTECTION

    if category in _LABOR_CATEGORIES and plaintiff == "individual":
        return ExemptionType.LABOR_DISPUTE

    if raw_category == "alimony" or (
        category == "family"
        and "алимент" in f"{state.get('claims', '')} {state.get('facts', '')}".lower()
    ):
        return ExemptionType.ALIMONY_PLAINTIFF

    return ExemptionType.NONE


def _resolve_both_alimony(state: dict[str, Any]) -> bool:
    if (state.get("case_category") or "").lower() == "alimony_children_and_plaintiff":
        return True
    text = f"{state.get('claims', '')} {state.get('facts', '')}".lower()
    return "алимент" in text and ("истц" in text or "взыскан" in text and "дет" in text)


def _resolve_debtor_bankruptcy(state: dict[str, Any]) -> bool:
    return (state.get("case_category") or "").lower() == "bankruptcy_debtor"


def _resolve_claim_amount(state: dict[str, Any]) -> float:
    amount = _to_float(state.get("total_claim", 0))
    if amount <= 0:
        amount = (
            _to_float(state.get("principal_amount", 0))
            + _to_float(state.get("penalty_amount", 0))
            + _to_float(state.get("interest_amount", 0))
            + _to_float(state.get("moral_damage", 0))
        )
    return amount


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        cleaned = re.sub(r"[^\d.,]", "", value)
        if "." in cleaned and "," in cleaned:
            if cleaned.rindex(".") > cleaned.rindex(","):
                cleaned = cleaned.replace(",", "")
            else:
                cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            if cleaned.count(",") == 1 and len(cleaned.split(",")[1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0
