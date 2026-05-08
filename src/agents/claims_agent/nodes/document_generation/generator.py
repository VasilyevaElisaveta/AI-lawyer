"""
Модуль генерации документов: исковых заявлений и претензий.
"""
import os
from typing import Any

from logger import LoggerFactory

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ...state import ClaimsAgentState
from ...prompts import (
    GENERATOR_HUMAN,
    GENERATOR_REWORK_HUMAN,
    GENERATOR_SYSTEM,
    COMPLAINT_GENERATOR_HUMAN,
    COMPLAINT_GENERATOR_SYSTEM,
    COMPLAINT_GENERATOR_REWORK_HUMAN,
    render_template,
)


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


def generator_node(state: ClaimsAgentState) -> dict[str, Any]:
    """Узел графа: генерация текста документа (иск или претензия)."""
    document_type = state.get("document_type", "lawsuit")
    logger.info("Generator node started (document_type=%s)", document_type)

    if document_type == "complaint":
        pass
        return _generate_complaint(state)
    return _generate_lawsuit(state)


# ═══════════════════════════════════════════════════════════════
#  Генерация искового заявления (существующая логика)
# ═══════════════════════════════════════════════════════════════

def _generate_lawsuit(
        state: ClaimsAgentState,
        llm,
        config: RunnableConfig
    ) -> dict[str, Any]:
    """Генерация искового заявления."""
    qa_feedback = state.get("qa_feedback", "")
    qa_attempts = state.get("qa_attempts", 0)

    variables = _collect_lawsuit_variables(state)

    if qa_feedback and qa_attempts > 0:
        logger.info("  Re-generating lawsuit after QA feedback (attempt %d)", qa_attempts)
        original_prompt = render_template(GENERATOR_HUMAN, variables)
        prompt = render_template(
            GENERATOR_REWORK_HUMAN,
            {
                "generated_document": state.get("generated_document", ""),
                "qa_feedback": qa_feedback,
                "original_prompt_data": original_prompt,
            },
        )
        system = GENERATOR_SYSTEM
    else:
        prompt = render_template(GENERATOR_HUMAN, variables)
        system = GENERATOR_SYSTEM

    try:
        response = llm.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=prompt),
            ],
            config=config,
        )
        content = response.content
        logger.info("  Lawsuit generated, length: %d chars", len(content))
        return {"generated_document": content}
    except Exception as e:
        logger.error("Lawsuit generator failed: %s", e)
        return {"error": f"Ошибка генерации искового заявления: {e}"}


# ═══════════════════════════════════════════════════════════════
#  Генерация претензии
# ═══════════════════════════════════════════════════════════════

def _generate_complaint(
        state: ClaimsAgentState,
        llm,
        config: RunnableConfig
    ) -> dict[str, Any]:
    """Генерация досудебной претензии."""
    qa_feedback = state.get("qa_feedback", "")
    qa_attempts = state.get("qa_attempts", 0)

    variables = _collect_complaint_variables(state)

    if qa_feedback and qa_attempts > 0:
        logger.info("  Re-generating complaint after QA feedback (attempt %d)", qa_attempts)
        original_prompt = render_template(COMPLAINT_GENERATOR_HUMAN, variables)
        prompt = render_template(
            COMPLAINT_GENERATOR_REWORK_HUMAN,
            {
                "generated_document": state.get("generated_document", ""),
                "qa_feedback": qa_feedback,
                "original_prompt_data": original_prompt,
            },
        )
        system = COMPLAINT_GENERATOR_SYSTEM
    else:
        prompt = render_template(COMPLAINT_GENERATOR_HUMAN, variables)
        system = COMPLAINT_GENERATOR_SYSTEM

    try:
        content = llm.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=prompt),
            ],
            config=config,
        )
        logger.info("  Complaint generated, length: %d chars", len(content))
        return {"generated_document": content}
    except Exception as e:
        logger.error("Complaint generator failed: %s", e)
        return {"error": f"Ошибка генерации претензии: {e}"}


# ═══════════════════════════════════════════════════════════════
#  Сборка переменных для шаблонов
# ═══════════════════════════════════════════════════════════════

def _collect_lawsuit_variables(state: ClaimsAgentState) -> dict[str, Any]:
    """Собирает все переменные для шаблона искового заявления."""
    from claims_agent.nodes.document_generation.calc import _fmt

    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    classification = state.get("classification_data", {})

    court_jurisdiction = classification.get("court_jurisdiction", "general")
    total_claim_value = state.get("total_claim", 0.0)
    case_type = classification.get("case_type", "civil")

    if (case_type == "civil"
            and court_jurisdiction == "general"
            and 0 < total_claim_value <= 100_000):
        logger.info(
            "  Автокоррекция: цена иска %.2f руб. < 100 000 руб. "
            "→ меняем подсудность с 'general' на 'magistrate'",
            total_claim_value
        )
        court_jurisdiction = "magistrate"

    court_info = state.get("court_info", "")
    if not court_info or "[НЕ УКАЗАНО]" in court_info:
        court_info = _infer_court_name(state, override_jurisdiction=court_jurisdiction)
        logger.info("  Court auto-inferred: %s", court_info[:100])

    attachments_list = _generate_attachments_list(state)
    risk_context = _build_risk_context(state, classification)

    return {
        "plaintiff_info": state.get("plaintiff_info", "[НЕ УКАЗАНО]"),
        "defendant_info": state.get("defendant_info", "[НЕ УКАЗАНО]"),
        "third_parties_info": state.get("third_parties_info", "не заявлены"),
        "court_info": court_info,
        "case_category": classification.get("case_category", state.get("case_category", "")),
        "case_subcategory": classification.get("case_subcategory", ""),
        "court_jurisdiction": court_jurisdiction,
        "proceeding_type": classification.get("proceeding_type", "lawsuit"),
        "facts": state.get("facts", "[НЕ УКАЗАНО]"),
        "documents": state.get("documents", "[НЕ УКАЗАНО]"),
        "claims": state.get("claims", "[НЕ УКАЗАНО]"),
        "principal_amount": _amount("principal_amount"),
        "penalty_amount": _amount("penalty_amount"),
        "interest_amount": _amount("interest_amount"),
        "moral_damage": _amount("moral_damage"),
        "court_expenses": _amount("court_expenses"),
        "state_duty": _amount("state_duty"),
        "total_claim": _amount("total_claim"),
        "applicable_laws": state.get("applicable_laws", "[НЕ ОПРЕДЕЛЕНЫ]"),
        "legal_positions": state.get("legal_positions", ""),
        "pretrial_settlement": state.get("pretrial_settlement", "не проводилось"),
        "calculation_details": state.get("calculation_details", ""),
        "attachments_list": attachments_list,
        "risk_warnings": risk_context["warnings"],
        "procedural_requirements": risk_context["requirements"],
        "classification_notes": risk_context["notes"],
    }


def _collect_complaint_variables(state: ClaimsAgentState) -> dict[str, Any]:
    """Собирает все переменные для шаблона претензии."""
    from claims_agent.nodes.document_generation.calc import _fmt

    def _amount(key: str) -> str:
        val = state.get(key, 0)
        if isinstance(val, (int, float)) and val > 0:
            return _fmt(val)
        return "0"

    classification = state.get("classification_data", {})

    # Тип и сфера претензии (из state или из classification)
    complaint_type = state.get("complaint_type", "")
    if not complaint_type:
        claim_nature = classification.get("claim_nature", "property")
        complaint_type = "monetary" if claim_nature in ("property", "mixed") else "non_monetary"

    complaint_sphere = state.get("complaint_sphere", "")
    if not complaint_sphere:
        category = classification.get("case_category", state.get("case_category", "other"))
        complaint_sphere = _infer_complaint_sphere(category)

    # Срок ответа
    response_deadline = state.get("complaint_response_deadline")
    deadline_basis = state.get("complaint_deadline_basis", "")
    if not response_deadline:
        response_deadline, deadline_basis = _infer_response_deadline(
            complaint_sphere,
            classification.get("case_category", state.get("case_category", ""))
        )

    # Способ отправки
    sending_method = state.get("complaint_sending_method", "mail")
    sending_method_label = {
        "in_person": "лично под роспись",
        "mail": "заказным письмом с уведомлением о вручении и описью вложения",
        "electronic": "в электронном виде (при условии наличия ЭЦП / договорного допущения)",
    }.get(sending_method, "заказным письмом с уведомлением о вручении и описью вложения")

    # Список приложений для претензии
    attachments_list = _generate_complaint_attachments_list(state)

    return {
        "sender_info": state.get("plaintiff_info", "[НЕ УКАЗАНО]"),
        "recipient_info": state.get("defendant_info", "[НЕ УКАЗАНО]"),
        "facts": state.get("facts", "[НЕ УКАЗАНО]"),
        "documents": state.get("documents", "[НЕ УКАЗАНО]"),
        "claims": state.get("claims", "[НЕ УКАЗАНО]"),
        "complaint_type": complaint_type,
        "complaint_sphere": complaint_sphere,
        "sending_method": sending_method,
        "sending_method_label": sending_method_label,
        "response_deadline": str(response_deadline),
        "deadline_basis": deadline_basis,
        "principal_amount": _amount("principal_amount"),
        "penalty_amount": _amount("penalty_amount"),
        "interest_amount": _amount("interest_amount"),
        "moral_damage": _amount("moral_damage"),
        "applicable_laws": state.get("applicable_laws", "[НЕ ОПРЕДЕЛЕНЫ]"),
        "legal_positions": state.get("legal_positions", ""),
        "calculation_details": state.get("calculation_details", ""),
        "attachments_list": attachments_list,
        "case_category": classification.get("case_category", state.get("case_category", "")),
    }


# ═══════════════════════════════════════════════════════════════
#  Утилиты для претензии
# ═══════════════════════════════════════════════════════════════

def _infer_complaint_sphere(category: str) -> str:
    """Определяет сферу претензии по категории дела."""
    _CONSUMER_CATS = {
        "consumer_goods", "consumer_services", "financial_services",
        "housing", "transport",
    }
    _LABOR_CATS = {"dismissal", "salary", "discrimination", "labor_other"}
    _COMMERCIAL_CATS = {
        "supply", "construction", "services", "lease", "credit",
        "agency", "commission", "insurance", "corporate_governance",
        "shareholder_dispute", "dividend", "debt_collection",
    }
    if category in _CONSUMER_CATS:
        return "consumer"
    if category in _LABOR_CATS:
        return "labor"
    if category in _COMMERCIAL_CATS:
        return "commercial"
    return "other"


def _infer_response_deadline(sphere: str, category: str) -> tuple[int, str]:
    """
    Определяет срок ответа на претензию (в днях) и основание.

    Основные источники:
    - ЗоЗПП: 10 дней (некачественный товар), 30 дней (услуги)
    - АПК РФ ст. 4: 30 дней (коммерческие споры)
    - ТК РФ ст. 382: 10 дней (трудовые споры)
    - ГК РФ ст. 797: 30 дней (перевозки)
    """
    if sphere == "consumer":
        if category == "consumer_goods":
            return 10, "ст. 22 Закона РФ «О защите прав потребителей»"
        if category in ("consumer_services", "housing"):
            return 30, "ст. 31 Закона РФ «О защите прав потребителей»"
        if category == "transport":
            return 30, "ст. 797 ГК РФ"
        return 10, "ст. 22 Закона РФ «О защите прав потребителей»"
    if sphere == "labor":
        return 10, "ст. 382 ТК РФ (рекомендуемый срок для обращения до КТС)"
    if sphere == "commercial":
        return 30, "ч. 5 ст. 4 АПК РФ (обязательный досудебный порядок)"
    return 30, "ст. 4 АПК РФ / общая практика"


def _generate_complaint_attachments_list(state: ClaimsAgentState) -> str:
    """
    Генерирует перечень приложений к претензии.

    Стандартный состав:
    1. Копия договора (основания претензии)
    2. Документы, подтверждающие нарушение (акты, накладные, платёжки)
    3. Расчёт суммы (если денежное требование)
    4. Доверенность (если подписывает представитель)
    """
    attachments = []
    counter = 1

    # 1. Документы-основания из поля documents
    user_docs = state.get("documents", "")
    if user_docs and user_docs not in ("[НЕ УКАЗАНО]", ""):
        doc_list = _parse_document_list(user_docs)
        for doc_name in doc_list:
            attachments.append(f"{counter}. {doc_name} — копия, [КОЛ-ВО ЛИСТОВ] л.")
            counter += 1

    # 2. Расчёт суммы (если денежная претензия)
    principal = state.get("principal_amount", 0)
    if isinstance(principal, (int, float)) and principal > 0:
        attachments.append(f"{counter}. Расчёт суммы претензии — 1 экз.")
        counter += 1

    # 3. Доверенность (если представитель)
    sender_info = state.get("plaintiff_info", "")
    if any(kw in sender_info.lower() for kw in ["представитель", "доверенность", "адвокат"]):
        attachments.append(f"{counter}. Доверенность представителя — копия, 1 экз.")
        counter += 1

    if not attachments:
        return "[ПЕРЕЧЕНЬ ПРИЛОЖЕНИЙ — ЗАПОЛНИТЬ ВРУЧНУЮ]"

    return "\n".join(attachments)


def _parse_document_list(text: str) -> list[str]:
    import re
    cleaned = re.sub(r"^\s*[\d\-•.]+\s*", "", text, flags=re.MULTILINE)
    items = re.split(r"[;\n]", cleaned)
    return [item.strip() for item in items if item.strip()]


# ═══════════════════════════════════════════════════════════════
#  Утилиты для искового заявления (перенесены из оригинала)
# ═══════════════════════════════════════════════════════════════

def _infer_court_name(
    state: ClaimsAgentState,
    override_jurisdiction: str | None = None
) -> str:
    classification = state.get("classification_data", {})
    jurisdiction = override_jurisdiction or classification.get("court_jurisdiction", "general")

    plaintiff_info = state.get("plaintiff_info", "")
    defendant_info = state.get("defendant_info", "")

    city, district = _extract_location(plaintiff_info, defendant_info, jurisdiction)

    if jurisdiction == "magistrate":
        return (
            f"Мировому судье судебного участка № [НОМЕР УЧАСТКА]\n"
            f"{district} {city}"
        )
    elif jurisdiction == "general":
        return f"{district} {city}"
    elif jurisdiction == "arbitration":
        if "Москв" in defendant_info:
            return "Арбитражный суд города Москвы"
        elif "Санкт-Петербург" in defendant_info or "СПб" in defendant_info:
            return "Арбитражный суд города Санкт-Петербурга"
        elif city and "город" in city.lower():
            return f"Арбитражный суд {city.replace('г. ', 'города ')}"
        else:
            return "Арбитражный суд [СУБЪЕКТ РФ — ТРЕБУЕТСЯ УТОЧНЕНИЕ]"
    elif jurisdiction == "administrative":
        return f"{district} {city}\n(по административному делу)"

    return "[НАИМЕНОВАНИЕ СУДА — ТРЕБУЕТСЯ УКАЗАТЬ ВРУЧНУЮ]"


def _extract_location(plaintiff_info: str, defendant_info: str, jurisdiction: str) -> tuple[str, str]:
    import re

    if jurisdiction == "arbitration":
        primary_info = defendant_info
        secondary_info = plaintiff_info
    else:
        primary_info = plaintiff_info
        secondary_info = defendant_info

    address_patterns = [
        r"(?:место жительства|адрес места жительства)[:\s]+.*?(?:г\.|город)\s*([А-ЯЁ][а-яё\-]+)",
        r"(?:адрес|проживает|зарегистрирован)[:\s]+.*?(?:г\.|город)\s*([А-ЯЁ][а-яё\-]+)",
    ]

    for pattern in address_patterns:
        match = re.search(pattern, primary_info, re.IGNORECASE)
        if not match:
            match = re.search(pattern, secondary_info, re.IGNORECASE)
        if match:
            return _format_court_by_city(match.group(1))

    exclude_patterns = r"(?:место рождения|родился|родилась)"
    for info in [primary_info, secondary_info]:
        sentences = re.split(r"[,.]", info)
        for sentence in sentences:
            if re.search(exclude_patterns, sentence, re.IGNORECASE):
                continue
            match = re.search(r"(?:г\.|город)\s*([А-ЯЁ][а-яё\-]+)", sentence, re.IGNORECASE)
            if match:
                return _format_court_by_city(match.group(1))

    logger.warning("  Город не найден в адресах сторон")
    return "г. [ГОРОД]", "[НАЗВАНИЕ] районный суд"


def _format_court_by_city(city_name: str) -> tuple[str, str]:
    return f"г. {city_name}", f"{city_name}ский районный суд"


def _generate_attachments_list(state: ClaimsAgentState) -> str:
    attachments = []
    counter = 1
    classification = state.get("classification_data", {})

    num_copies = _count_required_copies(state)
    if num_copies > 0:
        attachments.append(f"{counter}. Копия искового заявления — {num_copies} экз.")
        counter += 1

    state_duty = state.get("state_duty", 0.0)
    if state_duty > 0:
        from claims_agent.nodes.document_generation.calc import _fmt
        attachments.append(
            f"{counter}. Платёжное поручение (квитанция) об уплате государственной пошлины "
            f"на сумму {_fmt(state_duty)} руб. — 1 экз."
        )
        counter += 1

    if classification.get("pretrial_required"):
        attachments.append(
            f"{counter}. Копия претензии с отметкой о вручении ответчику "
            "(почтовая квитанция с описью вложения) — 1 экз."
        )
        counter += 1
        pretrial = state.get("pretrial_settlement", "")
        if pretrial and any(kw in pretrial.lower() for kw in ["ответ", "отказ", "получен"]):
            attachments.append(f"{counter}. Ответ на претензию от ответчика (при наличии) — 1 экз.")
            counter += 1

    if classification.get("claim_nature") in ["property", "mixed"]:
        attachments.append(f"{counter}. Расчёт исковых требований — 1 экз.")
        counter += 1

    user_docs = state.get("documents", "")
    if user_docs and user_docs not in ("[НЕ УКАЗАНО]", ""):
        for doc_name in _parse_document_list(user_docs):
            if any(kw in doc_name.lower() for kw in
                   ["претенз", "квитанц", "пошлин", "расчет", "расчёт", "копи"]):
                continue
            attachments.append(f"{counter}. {doc_name} — [КОЛ-ВО ЭКЗЕМПЛЯРОВ И ЛИСТОВ]")
            counter += 1

    plaintiff_info = state.get("plaintiff_info", "")
    if any(kw in plaintiff_info.lower() for kw in ["представитель", "доверенность", "адвокат"]):
        attachments.append(f"{counter}. Доверенность представителя — 1 экз.")
        counter += 1

    if not attachments:
        return "[ПЕРЕЧЕНЬ ПРИЛОЖЕНИЙ ТРЕБУЕТСЯ ДОПОЛНИТЬ]"

    return "\n".join(attachments)


def _count_required_copies(state: ClaimsAgentState) -> int:
    count = 0
    defendant_info = state.get("defendant_info", "")
    count += defendant_info.lower().count("ответчик")
    if count == 0 and defendant_info:
        count = 1
    third_parties = state.get("third_parties_info", "")
    if third_parties and third_parties not in ("не заявлены", ""):
        count += third_parties.lower().count("лицо")
        count += third_parties.lower().count("третий")
    return max(count, 1)


def _build_risk_context(state: ClaimsAgentState, classification: dict) -> dict[str, str]:
    warnings = []
    requirements = []
    notes = []

    if classification.get("pretrial_required"):
        deadline = classification.get("pretrial_deadline_days", 30)
        completed = classification.get("pretrial_completed", False)
        if not completed:
            warnings.append(
                f"⚠КРИТИЧНО: Обязателен досудебный порядок урегулирования спора "
                f"(срок ответа на претензию: {deadline} дней). "
                f"Без доказательства соблюдения претензионного порядка иск будет возвращён "
                f"(ст. 135 ГПК РФ / ст. 129 АПК РФ)."
            )
        requirements.append(
            f"В описательной части обязательно указать: \n"
            f"  • Дату направления претензии ответчику\n"
            f"  • Способ направления (почта России, email, лично в руки)\n"
            f"  • Дату получения ответа либо дату истечения срока ({deadline} дней)"
        )

    if classification.get("claim_nature") == "mixed":
        warnings.append(
            "⚠ВНИМАНИЕ: Исковое заявление содержит требования смешанного характера "
            "(имущественные + неимущественные). По НК РФ ст. 333.20 уплачиваются "
            "ДВЕ государственные пошлины!"
        )

    if classification.get("proceeding_type") == "simplified":
        notes.append(
            "Дело подлежит рассмотрению в порядке упрощённого производства "
            "(ГПК РФ ст. 232.2 / АПК РФ гл. 29). Срок рассмотрения: 2 месяца."
        )

    if classification.get("court_jurisdiction") == "magistrate":
        notes.append("Дело подсудно мировому судье (ГПК РФ ст. 23). Цена иска не превышает 100 000 рублей.")

    if classification.get("can_use_writ_proceedings"):
        notes.append(
            "РЕКОМЕНДАЦИЯ: Возможна подача заявления о вынесении судебного приказа "
            "(ГПК РФ гл. 11 / АПК РФ гл. 29.1). Срок вынесения: 5 дней."
        )

    for w in classification.get("warnings", []):
        if "КРИТИЧНО" in w or "ОШИБКА" in w:
            warnings.append(w)

    return {
        "warnings": "\n\n".join(warnings) if warnings else "",
        "requirements": "\n\n".join(requirements) if requirements else "",
        "notes": "\n".join(f"• {note}" for note in notes) if notes else "",
    }
