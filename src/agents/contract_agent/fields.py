from __future__ import annotations

COMMON_FIELDS = [
    "facts",
    "applicable_laws",
    "principal_amount",
    "loan_interest_amount",
    "penalty_amount",
    "interest_amount",
    "moral_damage",
    "court_expenses",
    "state_duty",
    "total_claim",
    "total_amount",
    "response_deadline",
    "request_ongoing_penalty",
]

REQUIRED_FIELDS_BY_TYPE = {
    "lawsuit": [
        "plaintiff_info",
        "defendant_info",
        "facts",
        "claims",
        "applicable_laws",
    ],
    "pretrial_claim": [
        "sender_info",
        "recipient_info",
        "facts",
        "sender_demands",
        "applicable_laws",
        "response_deadline",
    ],
}

FIELD_LABELS = {
    "plaintiff_info": "Сведения об истце",
    "defendant_info": "Сведения об ответчике",
    "claims": "Требования по иску",
    "sender_info": "Сведения об отправителе",
    "recipient_info": "Сведения о получателе",
    "sender_demands": "Требования по претензии",
    "facts": "Факты дела",
    "applicable_laws": "Применимые нормы",
    "response_deadline": "Срок ответа",
    "principal_amount": "Основная сумма",
    "loan_interest_amount": "Сумма процентов",
    "penalty_amount": "Сумма пени",
    "interest_amount": "Сумма процентов по займу",
    "moral_damage": "Моральный вред",
    "court_expenses": "Судебные расходы",
    "state_duty": "Государственная пошлина",
    "total_claim": "Общая сумма иска",
    "total_amount": "Общая сумма требований",
    "request_ongoing_penalty": "Прошу взыскать текущую пеню",
}

STOP_PHRASES = [
    "не хочу обсуждать",
    "больше не хочу",
    "хватит",
    "стоп",
    "перестань",
    "закончить",
    "закончи",
    "выход",
    "закончим",
]

BOOLEAN_FIELDS = ["request_ongoing_penalty"]
NUMERIC_FIELDS = [
    "principal_amount",
    "loan_interest_amount",
    "penalty_amount",
    "interest_amount",
    "moral_damage",
    "court_expenses",
    "state_duty",
    "total_claim",
    "total_amount",
]
