"""
Модуль классификации дела:
  • тип судопроизводства (civil / arbitration / administrative)
  • категория и подкатегория спора
  • характер требований (имущественные / неимущественные / смешанные)
  • подсудность (общая юрисдикция / арбитраж / мировой судья / административная)
  • порядок производства (исковое / особое / приказное / упрощённое)
  • проверка досудебного порядка
"""
import os
import json
from dataclasses import dataclass, asdict, field
from typing import Any, Literal, cast

from logger import LoggerFactory

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ...state import ClaimsAgentState
from ...prompts import (
    CLASSIFICATION_HUMAN,
    CLASSIFICATION_SYSTEM,
    render_template,
)

logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


# ═══════════════════════════════════════════════════════════════
#  Типы и константы
# ═══════════════════════════════════════════════════════════════

# Type aliases для Literal типов
CaseType = Literal["civil", "arbitration", "administrative"]
ClaimNature = Literal["property", "non_property", "mixed"]
CourtJurisdiction = Literal["general", "arbitration", "magistrate", "administrative"]
ProceedingType = Literal["lawsuit", "special", "writ", "simplified"]
PartyType = Literal["individual", "legal_entity", "ip", "state", "unknown"]


@dataclass
class ClassificationResult:
    """Результат классификации дела."""

    # Основная классификация (обязательные поля без default)
    case_type: CaseType
    case_category: str
    claim_nature: ClaimNature
    court_jurisdiction: CourtJurisdiction
    proceeding_type: ProceedingType
    plaintiff_type: PartyType
    defendant_type: PartyType
    pretrial_required: bool

    # Опциональные поля (с default значениями)
    case_subcategory: str | None = None
    pretrial_deadline_days: int | None = None
    pretrial_completed: bool = False
    pretrial_notes: str = ""
    can_use_writ_proceedings: bool = False
    can_use_simplified: bool = False
    reasoning: str = ""
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# Валидные значения категорий
_VALID_CATEGORIES = {
    # Договорные споры
    "supply", "construction", "services", "lease", "credit",
    "insurance", "transport", "agency", "commission",

    # Потребительские
    "consumer_goods", "consumer_services", "financial_services",

    # Трудовые
    "dismissal", "salary", "discrimination", "labor_other",

    # Корпоративные
    "corporate_governance", "shareholder_dispute", "dividend",

    # Специальные
    "inheritance", "land", "housing", "family",
    "ip_copyright", "ip_trademark", "ip_patent",
    "bankruptcy", "tort", "unjust_enrichment",

    # Публично-правовые
    "administrative_fine", "licensing", "permit",

    # Общее
    "debt_collection", "property_dispute", "other"
}

_VALID_CASE_TYPES: set[CaseType] = {"civil", "arbitration", "administrative"}
_VALID_CLAIM_NATURES: set[ClaimNature] = {"property", "non_property", "mixed"}
_VALID_JURISDICTIONS: set[CourtJurisdiction] = {"general", "arbitration", "magistrate", "administrative"}
_VALID_PROCEEDINGS: set[ProceedingType] = {"lawsuit", "special", "writ", "simplified"}
_VALID_PARTY_TYPES: set[PartyType] = {"individual", "legal_entity", "ip", "state", "unknown"}


# ═══════════════════════════════════════════════════════════════
#  Основная функция узла графа
# ═══════════════════════════════════════════════════════════════

def classification_node(
        state: ClaimsAgentState,
        llm, 
        config: RunnableConfig | None = None) -> dict[str, Any]:
    """Узел графа: классификация дела."""
    logger.info("Classification node started")

    # Идемпотентность: если уже классифицировано — пропускаем
    # Проверяем наличие новых полей классификации
    if (state.get("case_type") and
        state.get("case_category") and
        state.get("classification_data")):
        logger.info("  Already classified — skipping")
        return {}

    # Подготовка данных для промпта
    prompt_vars = {
        "plaintiff_info": state.get("plaintiff_info", ""),
        "defendant_info": state.get("defendant_info", ""),
        "facts": state.get("facts", ""),
        "claims": state.get("claims", ""),
        "pretrial_settlement": state.get("pretrial_settlement", ""),
        "total_claim": state.get("total_claim", 0.0),
        "principal_amount": state.get("principal_amount", 0.0),
        "penalty_amount": state.get("penalty_amount", 0.0),
        "interest_amount": state.get("interest_amount", 0.0),
        "moral_damage": state.get("moral_damage", 0.0),
    }

    prompt = render_template(CLASSIFICATION_HUMAN, prompt_vars)

    try:
        response = llm.invoke(
            [
                SystemMessage(content=CLASSIFICATION_SYSTEM),
                HumanMessage(content=prompt),
            ],
            config=config    
        )
        content = response.content
        result = _parse_and_validate_classification(content, state)

        logger.info(
            "  Classified: type=%s category=%s/%s jurisdiction=%s pretrial_req=%s confidence=%.2f",
            result.case_type,
            result.case_category,
            result.case_subcategory or "-",
            result.court_jurisdiction,
            result.pretrial_required,
            result.confidence,
        )

        if result.warnings:
            logger.warning("  Warnings: %s", "; ".join(result.warnings))

        # Преобразуем dataclass в dict и возвращаем обновления state
        classification_dict = asdict(result)

        return {
            # Сохраняем полную структуру классификации
            "classification_data": classification_dict,

            # Дублируем ключевые поля в корень state для обратной совместимости
            "case_type": result.case_type,
            "case_category": result.case_category,
            "is_property_dispute": result.claim_nature in ["property", "mixed"],
        }

    except Exception as e:
        logger.error("Classification failed: %s — using safe defaults", e, exc_info=True)
        return _create_fallback_classification()


# ═══════════════════════════════════════════════════════════════
#  Парсинг и валидация ответа LLM
# ═══════════════════════════════════════════════════════════════

def _parse_and_validate_classification(
    text: str,
    state: ClaimsAgentState
) -> ClassificationResult:
    """
    Извлекает JSON из ответа LLM, валидирует и обогащает данные.

    Args:
        text: Ответ от LLM (может содержать markdown)
        state: Текущее состояние для дополнительной валидации

    Returns:
        Валидированный ClassificationResult

    Raises:
        ValueError: Если JSON невалиден или отсутствуют обязательные поля
    """
    # Извлечение JSON из markdown-блока или чистого текста
    data = _extract_json(text)

    # Валидация обязательных полей
    required_fields = [
        "case_type", "case_category", "claim_nature",
        "court_jurisdiction", "proceeding_type",
        "plaintiff_type", "defendant_type",
        "pretrial_required"
    ]

    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields from LLM response: {missing}")

    # Валидация и нормализация enum-полей с явным cast к Literal типам
    result = ClassificationResult(
        case_type=cast(
            CaseType,
            _validate_enum(data["case_type"], _VALID_CASE_TYPES, "civil")
        ),
        case_category=_validate_enum(
            data["case_category"],
            _VALID_CATEGORIES,
            "other"
        ),
        case_subcategory=data.get("case_subcategory"),
        claim_nature=cast(
            ClaimNature,
            _validate_enum(data["claim_nature"], _VALID_CLAIM_NATURES, "property")
        ),
        court_jurisdiction=cast(
            CourtJurisdiction,
            _validate_enum(data["court_jurisdiction"], _VALID_JURISDICTIONS, "general")
        ),
        proceeding_type=cast(
            ProceedingType,
            _validate_enum(data["proceeding_type"], _VALID_PROCEEDINGS, "lawsuit")
        ),
        plaintiff_type=cast(
            PartyType,
            _validate_enum(data["plaintiff_type"], _VALID_PARTY_TYPES, "unknown")
        ),
        defendant_type=cast(
            PartyType,
            _validate_enum(data["defendant_type"], _VALID_PARTY_TYPES, "unknown")
        ),
        pretrial_required=bool(data["pretrial_required"]),
        pretrial_deadline_days=data.get("pretrial_deadline_days"),
        pretrial_completed=bool(data.get("pretrial_completed", False)),
        pretrial_notes=data.get("pretrial_notes", ""),
        can_use_writ_proceedings=bool(data.get("can_use_writ_proceedings", False)),
        can_use_simplified=bool(data.get("can_use_simplified", False)),
        reasoning=data.get("reasoning", ""),
        confidence=float(data.get("confidence", 1.0)),
        warnings=data.get("warnings", []),
        recommendations=data.get("recommendations", [])
    )

    # Пост-валидация и обогащение
    result = _enrich_classification(result, state)
    result = _validate_logical_consistency(result, state)

    return result


def _extract_json(text: str) -> dict[str, Any]:
    """Извлекает JSON из markdown-блока или plain text."""
    import re

    # Попытка 1: Markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        raw = match.group(1)
    else:
        # Попытка 2: Первая пара фигурных скобок
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in LLM response")
        raw = text[start:end]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON from LLM: %s\nRaw text: %s", e, raw[:500])
        raise ValueError(f"Invalid JSON from LLM: {e}") from e


def _validate_enum(
    value: Any,
    valid_values: set[str],
    default: str
) -> str:
    """Валидирует значение против whitelist, возвращает default при ошибке."""
    if value in valid_values:
        return value

    logger.warning(
        "Invalid enum value '%s', expected one of %s — using default '%s'",
        value, valid_values, default
    )
    return default


# ═══════════════════════════════════════════════════════════════
#  Обогащение и дополнительная валидация
# ═══════════════════════════════════════════════════════════════

def _enrich_classification(
    result: ClassificationResult,
    state: ClaimsAgentState
) -> ClassificationResult:
    """Дополняет классификацию на основе правил и данных из state."""

    # Автоопределение срока досудебного урегулирования, если LLM не указала
    if result.pretrial_required and result.pretrial_deadline_days is None:
        result.pretrial_deadline_days = _infer_pretrial_deadline(
            result.case_type,
            result.case_category
        )

    # Проверка возможности судебного приказа
    if not result.can_use_writ_proceedings:
        result.can_use_writ_proceedings = _check_writ_eligibility(result, state)

    # Проверка возможности упрощённого производства
    if not result.can_use_simplified:
        result.can_use_simplified = _check_simplified_eligibility(result, state)

    # Рекомендации на основе классификации
    if result.can_use_writ_proceedings:
        result.recommendations.append(
            "Возможна подача заявления о вынесении судебного приказа "
            "(упрощённая процедура без судебного заседания)"
        )

    if result.can_use_simplified and result.case_type == "arbitration":
        result.recommendations.append(
            "Дело может быть рассмотрено в порядке упрощённого производства "
            "(гл. 29 АПК РФ, срок — 2 месяца)"
        )

    return result


def _validate_logical_consistency(
    result: ClassificationResult,
    state: ClaimsAgentState
) -> ClassificationResult:
    """Проверяет логическую целостность классификации и добавляет warnings."""

    # Несоответствие case_type и court_jurisdiction
    if result.case_type == "arbitration" and result.court_jurisdiction not in ["arbitration"]:
        result.warnings.append(
            f"Несоответствие: арбитражное дело, но юрисдикция {result.court_jurisdiction}"
        )
        result.confidence *= 0.7

    if result.case_type == "administrative" and result.court_jurisdiction != "administrative":
        result.warnings.append(
            f"Несоответствие: административное дело, но юрисдикция {result.court_jurisdiction}"
        )
        result.confidence *= 0.7

    # Проверка подсудности мирового судьи по цене иска
    total_claim = state.get("total_claim", 0.0)
    if result.court_jurisdiction == "magistrate" and total_claim >= 100_000:
        result.warnings.append(
            f"ОШИБКА: Цена иска {total_claim:,.2f} руб. превышает 100 000 руб. — "
            "дело не подсудно мировому судье (ст. 23 ГПК РФ)"
        )
        # Автоисправление
        result.court_jurisdiction = cast(CourtJurisdiction, "general")
        result.confidence *= 0.6

    # Проверка family споров в арбитраже (невозможно)
    if result.case_category == "family" and result.case_type == "arbitration":
        result.warnings.append(
            "ОШИБКА: Семейные споры не подсудны арбитражным судам"
        )
        # Автоисправление
        result.case_type = cast(CaseType, "civil")
        result.court_jurisdiction = cast(CourtJurisdiction, "general")
        result.confidence *= 0.5

    # Проверка обязательного досудебного порядка
    if result.pretrial_required and not result.pretrial_completed:
        pretrial_data = state.get("pretrial_settlement", "")
        if not pretrial_data or pretrial_data.strip() in ["", "[НЕ УКАЗАНО]"]:
            result.warnings.append(
                f"КРИТИЧНО: Обязателен досудебный порядок ({result.case_category}), "
                f"но нет данных о претензии. Срок: {result.pretrial_deadline_days} дней. "
                "Иск будет возвращён по ст. 135 ГПК / 129 АПК!"
            )
            result.confidence *= 0.4

    # Проверка типов сторон для арбитража
    if result.case_type == "arbitration":
        if result.plaintiff_type == "individual" and result.defendant_type == "individual":
            if result.case_category not in ["bankruptcy", "corporate_governance"]:
                result.warnings.append(
                    "Сомнительно: арбитражное дело между физлицами без статуса ИП "
                    "(возможно, должно быть гражданское производство)"
                )
                result.confidence *= 0.7

    # Проверка смешанных требований и госпошлины
    if result.claim_nature == "mixed":
        result.recommendations.append(
            "ВНИМАНИЕ: Смешанные требования (имущественные + неимущественные). "
            "По НК РФ ст. 333.20 уплачиваются ОБЕ госпошлины!"
        )

    return result


# ═══════════════════════════════════════════════════════════════
#  Вспомогательные функции для обогащения
# ═══════════════════════════════════════════════════════════════

def _infer_pretrial_deadline(case_type: str, category: str) -> int | None:
    """
    Определяет срок досудебного урегулирования на основе категории дела.

    Справочник основных сроков:
    - АПК РФ ст. 4: 30 дней (общее правило для экономических споров)
    - ЗоЗПП: 10 дней (техсложные товары), 30 дней (прочее)
    - ОСАГО: 10 дней (ремонт) / 20 дней (выплата)
    - 44-ФЗ/223-ФЗ: 10 дней
    - Перевозка: 30 дней (ст. 797 ГК РФ)
    """
    PRETRIAL_DEADLINES: dict[tuple[str, str], int] = {
        # Арбитражные споры (АПК РФ ст. 4)
        ("arbitration", "*"): 30,

        # Потребительские споры
        ("civil", "consumer_goods"): 30,
        ("civil", "consumer_services"): 30,
        ("civil", "financial_services"): 10,  # часто ОСАГО, микрозаймы

        # Договорные споры
        ("*", "transport"): 30,  # ст. 797 ГК РФ
        ("*", "supply"): 30,

        # Публичные закупки
        ("arbitration", "contract"): 10,  # если 44-ФЗ/223-ФЗ (упрощение)
    }

    # Проверка по точному совпадению
    key = (case_type, category)
    if key in PRETRIAL_DEADLINES:
        return PRETRIAL_DEADLINES[key]

    # Проверка по wildcard
    for (ct, cat), days in PRETRIAL_DEADLINES.items():
        if (ct == "*" or ct == case_type) and (cat == "*" or cat == category):
            return days

    # Если не нашли конкретный срок — возвращаем None
    # (LLM должна была указать в reasoning)
    return None


def _check_writ_eligibility(
    result: ClassificationResult,
    state: ClaimsAgentState
) -> bool:
    """
    Проверяет возможность вынесения судебного приказа.

    ГПК РФ ст. 121-122.1: до 500 000 руб., бесспорные требования
    АПК РФ гл. 29.1: до 400 000 руб. (для ИП) / нет лимита (для ЮЛ по некоторым категориям)
    """
    total_claim = state.get("total_claim", 0.0)

    # ГПК: лимит 500к, только определённые категории
    if result.case_type == "civil":
        if total_claim > 500_000:
            return False

        # Разрешённые категории для приказа (ст. 122.1 ГПК)
        eligible_categories = {
            "debt_collection",  # долг по договору
            "salary",  # зарплата
            "consumer_services",  # услуги ЖКХ и т.п.
        }

        return result.case_category in eligible_categories

    # АПК: лимит 400к для ИП, 800к для ЮЛ (упрощение)
    if result.case_type == "arbitration":
        if result.plaintiff_type == "ip" and total_claim > 400_000:
            return False
        if result.plaintiff_type == "legal_entity" and total_claim > 800_000:
            return False

        # Бесспорность требования (договор, расписка и т.п.)
        facts = state.get("facts", "").lower()
        if any(keyword in facts for keyword in ["договор", "расписка", "задолженность"]):
            return True

    return False


def _check_simplified_eligibility(
    result: ClassificationResult,
    state: ClaimsAgentState
) -> bool:
    """
    Проверяет возможность упрощённого производства.

    АПК РФ гл. 29: до 400 000 руб. (ИП) / 2 000 000 руб. (ЮЛ)
    ГПК РФ ст. 232.2: определённые категории дел
    """
    total_claim = state.get("total_claim", 0.0)

    # АПК: упрощённое производство
    if result.case_type == "arbitration":
        if result.defendant_type == "ip" and total_claim <= 400_000:
            return True
        if result.defendant_type == "legal_entity" and total_claim <= 2_000_000:
            return True

        # Бесспорные требования могут быть рассмотрены упрощённо независимо от суммы
        if result.case_category in ["debt_collection", "supply"] and total_claim <= 10_000_000:
            return True

    # ГПК: упрощённое производство (ст. 232.2)
    if result.case_type == "civil":
        simplified_categories = {
            "consumer_goods",
            "consumer_services",
            "financial_services"
        }
        if result.case_category in simplified_categories and total_claim <= 100_000:
            return True

    return False


# ═══════════════════════════════════════════════════════════════
#  Fallback при ошибке
# ═══════════════════════════════════════════════════════════════

def _create_fallback_classification() -> dict[str, Any]:
    """Создаёт безопасную дефолтную классификацию при ошибке LLM."""
    result = ClassificationResult(
        case_type=cast(CaseType, "civil"),
        case_category="other",
        claim_nature=cast(ClaimNature, "property"),
        court_jurisdiction=cast(CourtJurisdiction, "general"),
        proceeding_type=cast(ProceedingType, "lawsuit"),
        plaintiff_type=cast(PartyType, "unknown"),
        defendant_type=cast(PartyType, "unknown"),
        pretrial_required=False,
        reasoning="Классификация не удалась, использованы значения по умолчанию",
        confidence=0.0,
        warnings=[
            "КРИТИЧНО: Автоматическая классификация не удалась. "
            "Требуется ручная проверка всех параметров!"
        ]
    )

    classification_dict = asdict(result)

    return {
        "classification_data": classification_dict,
        "case_type": result.case_type,
        "case_category": result.case_category,
        "is_property_dispute": True,
    }