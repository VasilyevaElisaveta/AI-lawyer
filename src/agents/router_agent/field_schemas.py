"""
Схемы обязательных полей для агентов, обрабатываемых маршрутизатором.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentFieldSpec:
    key: str
    title: str
    description: str
    required: bool = True


CLAIMS_AGENT_FIELDS: list[AgentFieldSpec] = [
    AgentFieldSpec(
        "plaintiff_info",
        "Истец / отправитель",
        "ФИО или наименование, адрес и контактные данные истца (отправителя претензии).",
    ),
    AgentFieldSpec(
        "defendant_info",
        "Ответчик / получатель",
        "ФИО или наименование, адрес ответчика (получателя претензии).",
    ),
    AgentFieldSpec(
        "facts",
        "Фактические обстоятельства",
        "Краткое изложение сути спора: что произошло, когда, какие действия сторон.",
    ),
    AgentFieldSpec(
        "claims",
        "Требования",
        "Что вы просите: взыскать сумму, признать право, обязать совершить действие и т.д.",
    ),
]

GENERAL_QUESTIONS_AGENT_FIELDS: list[AgentFieldSpec] = [
    AgentFieldSpec(
        "question",
        "Вопрос",
        "Сформулируйте юридический вопрос или опишите ситуацию, по которой нужна консультация.",
    ),
]

CATEGORY_TO_DOCUMENT_TYPE: dict[str, str] = {
    "claim": "lawsuit",
    "pretrial_claim": "complaint",
}

AGENT_FIELD_SCHEMAS: dict[str, list[AgentFieldSpec]] = {
    "claims_agent": CLAIMS_AGENT_FIELDS,
    "general_questions_agent": GENERAL_QUESTIONS_AGENT_FIELDS,
}

AGENT_TASK_LABELS: dict[str, str] = {
    "claims_agent": "подготовке искового заявления или досудебной претензии",
    "general_questions_agent": "консультации по общему юридическому вопросу",
}


def get_field_keys(agent: str) -> list[str]:
    return [f.key for f in AGENT_FIELD_SCHEMAS.get(agent, [])]


def build_missing_fields_message(
    agent: str,
    missing: list[AgentFieldSpec],
) -> str:
    task_label = AGENT_TASK_LABELS.get(agent, "запросу")
    lines = [
        f"Для продолжения работы над {task_label} укажите, пожалуйста, следующие данные:\n",
    ]
    for field in missing:
        lines.append(f"• **{field.title}** — {field.description}")
    lines.append(
        "\nВы можете прислать недостающие сведения одним сообщением "
        "или дополнить уже указанную информацию."
    )
    return "\n".join(lines)


def is_field_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, (dict, list)):
        return bool(value)
    return bool(value)
