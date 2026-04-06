# Валидные типы дел
_VALID_CASE_TYPES: tuple[str, ...] = ("civil", "arbitration")

# Валидные категории дел
_VALID_CATEGORIES: tuple[str, ...] = (
    "debt_collection",
    "debt",
    "employment",
    "consumer",
    "property",
    "family",
    "housing",
    "contract",
    "tort",
    "insurance",
    "other",
)

# Поля для договора
_CONTRACT_FIELDS: dict[str, str] = {
    "party_a_info": "party_a_info",
    "party_b_info": "party_b_info",
    "contract_subject": "contract_subject",
    "contract_terms": "contract_terms",
    "governing_law": "governing_law",
    "contract_amount": "contract_amount",
}

COMMON_FIELDS = [
    "contract_subject",
    "contract_terms",
    "governing_law",
    "contract_amount",
]

REQUIRED_FIELDS_BY_TYPE = {
    "contract": [
        "party_a_info",
        "party_b_info",
        "contract_subject",
        "contract_terms",
        "governing_law",
    ],
}

FIELD_LABELS = {
    "party_a_info": "Сведения о стороне А",
    "party_b_info": "Сведения о стороне Б",
    "contract_subject": "Предмет договора",
    "contract_terms": "Условия договора",
    "governing_law": "Применимое право",
    "contract_amount": "Сумма договора",
}

BOOLEAN_FIELDS = []
NUMERIC_FIELDS = [
    "contract_amount",
]
