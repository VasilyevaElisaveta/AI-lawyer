"""
Модуль расчётов.
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Any

from app.core.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════


def calculator_node(state: AgentState) -> dict[str, Any]:
    """
    Узел графа: математические расчёты.

    Ожидаемые параметры в state:
    - case_type: тип дела ('civil' или 'arbitration')
    - is_property_dispute: bool - имущественный ли спор
    - total_claim: сумма иска (для имущественных)
    - principal_amount, penalty_amount, interest_amount и др.
    """
    logger.info("Начало расчётов")

    result = {}

    try:
        # Расчёт госпошлины
        state_duty = _calculate_state_duty(state)

        # Расчёт неустойки (если есть параметры)
        penalty_calc = _calculate_penalty(state)

        # Расчёт процентов (если есть параметры)
        interest_calc = _calculate_interest(state)

        # Итоговая сумма иска
        total_claim = _calculate_total_claim(state, penalty_calc, interest_calc)

        # Формируем детальный расчёт для документа
        calculation_details = _format_calculation_details(
            state, state_duty, penalty_calc, interest_calc, total_claim
        )

        result = {
            "state_duty": state_duty,
            "total_claim": total_claim,
            "calculation_details": calculation_details
        }

        # Обновляем отдельные суммы, если были расчёты
        if penalty_calc.get("success"):
            result["penalty_amount"] = penalty_calc["penalty"]

        if interest_calc.get("success"):
            result["interest_amount"] = interest_calc["interest"]

        logger.info(f"Расчёт завершён: госпошлина={_fmt(state_duty)}, цена иска={_fmt(total_claim)}")

    except Exception as e:
        logger.error(f"Ошибка в расчётах: {e}", exc_info=True)
        result = {
            "error": f"Ошибка расчёта: {str(e)}",
            "state_duty": 0.0,
            "total_claim": 0.0,
            "calculation_details": ""
        }

    return result


def _calculate_state_duty(state: AgentState) -> float:
    """
    Расчёт госпошлины на основе параметров из state.

    Returns:
        размер госпошлины в рублях
    """
    case_type = state.get("case_type", "").lower()
    is_property = state.get("is_property_dispute", False)
    case_category = state.get("case_category", "").lower()

    # Специальные категории
    if case_category == "divorce":
        logger.debug("Госпошлина: расторжение брака")
        return 5_000.0

    if case_category == "alimony":
        logger.debug("Госпошлина: взыскание алиментов")
        return 150.0

    if case_category == "alimony_children_and_plaintiff":
        logger.debug("Госпошлина: взыскание алиментов на детей и истца")
        return 300.0

    # Имущественные споры - берём из total_claim
    if is_property:
        claim_amount = _to_float(state.get("total_claim", 0))

        # Если total_claim не указан, считаем сумму компонентов
        if claim_amount == 0:
            claim_amount = (
                _to_float(state.get("principal_amount", 0)) +
                _to_float(state.get("penalty_amount", 0)) +
                _to_float(state.get("interest_amount", 0)) +
                _to_float(state.get("moral_damage", 0))
            )

        if claim_amount <= 0:
            raise ValueError("Для имущественного спора не указана сумма иска")

        if case_type == "civil":
            duty = calc_state_duty_civil(claim_amount)
        elif case_type == "arbitration":
            duty = calc_state_duty_arbitration(claim_amount)
        else:
            raise ValueError(f"Неизвестный тип дела: {case_type}")

        logger.debug(
            f"Госпошлина (имущественный спор): "
            f"суд={case_type}, сумма={_fmt(claim_amount)}, пошлина={_fmt(duty)}"
        )
        return duty

    # Неимущественные споры
    else:
        # Для неимущественных нужно определить тип заявителя
        # Можно добавить в state или определить по контексту
        # Пока используем дефолтное значение для физлица
        applicant_type = "individual"  # можно добавить в AgentState

        duty = calc_state_duty_non_property(
            court_type=case_type,
            case_category=case_category,
            applicant_type=applicant_type
        )

        logger.debug(
            f"Госпошлина (неимущественный спор): "
            f"суд={case_type}, категория={case_category}, пошлина={_fmt(duty)}"
        )
        return duty


def _calculate_penalty(state: AgentState) -> dict[str, Any]:
    """
    Расчёт неустойки/пени на основе параметров из state.

    Returns:
        словарь с результатами расчёта или {"success": False}
    """
    principal = _to_float(state.get("principal_amount", 0))
    penalty_rate = _to_float(state.get("penalty_rate", 0))
    start_date = state.get("penalty_start_date", "")
    end_date = state.get("penalty_end_date", "")

    # Если нет всех необходимых параметров - пропускаем расчёт
    if not all([principal > 0, penalty_rate > 0, start_date, end_date]):
        return {"success": False}

    try:
        days = _days_between(start_date, end_date)
        penalty = principal * (penalty_rate / 100) * days

        logger.debug(
            f"Расчёт неустойки: основной долг={_fmt(principal)}, "
            f"ставка={penalty_rate}%, дней={days}, неустойка={_fmt(penalty)}"
        )

        return {
            "success": True,
            "principal": principal,
            "penalty_rate": penalty_rate,
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "penalty": penalty
        }
    except Exception as e:
        logger.error(f"Ошибка расчёта неустойки: {e}")
        return {"success": False, "error": str(e)}


def _calculate_interest(state: AgentState) -> dict[str, Any]:
    """
    Расчёт процентов по ст. 395 ГК РФ на основе параметров из state.

    Returns:
        словарь с результатами расчёта или {"success": False}
    """
    principal = _to_float(state.get("principal_amount", 0))
    start_date = state.get("interest_start_date", "")
    end_date = state.get("interest_end_date", "")
    cbr_rate = _to_float(state.get("cbr_key_rate", 0))

    # Если нет всех необходимых параметров - пропускаем расчёт
    if not all([principal > 0, start_date, end_date, cbr_rate > 0]):
        return {"success": False}

    try:
        days = _days_between(start_date, end_date)
        # Ставка уже в долях (0.16 = 16%)
        interest = principal * cbr_rate * (days / 365)

        logger.debug(
            f"Расчёт процентов: основной долг={_fmt(principal)}, "
            f"ставка ЦБ={cbr_rate * 100}%, дней={days}, проценты={_fmt(interest)}"
        )

        return {
            "success": True,
            "principal": principal,
            "rate": cbr_rate,
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "interest": interest
        }
    except Exception as e:
        logger.error(f"Ошибка расчёта процентов: {e}")
        return {"success": False, "error": str(e)}


def _calculate_total_claim(
    state: AgentState,
    penalty_calc: dict,
    interest_calc: dict
) -> float:
    """
    Расчёт итоговой цены иска.

    Returns:
        общая сумма требований
    """
    total = 0.0

    # Основной долг
    total += _to_float(state.get("principal_amount", 0))

    # Неустойка (берём из расчёта или из state)
    if penalty_calc.get("success"):
        total += penalty_calc["penalty"]
    else:
        total += _to_float(state.get("penalty_amount", 0))

    # Проценты (берём из расчёта или из state)
    if interest_calc.get("success"):
        total += interest_calc["interest"]
    else:
        total += _to_float(state.get("interest_amount", 0))

    # Моральный вред
    total += _to_float(state.get("moral_damage", 0))

    # НЕ включаем судебные расходы в цену иска
    # (они взыскиваются отдельно)

    logger.debug(f"Итоговая цена иска: {_fmt(total)}")
    return total


def _format_calculation_details(
    state: AgentState,
    state_duty: float,
    penalty_calc: dict,
    interest_calc: dict,
    total_claim: float
) -> str:
    """
    Формирование детального текста расчёта для вставки в документ.

    Returns:
        форматированный текст расчёта
    """
    lines = []

    # Основной долг
    principal = _to_float(state.get("principal_amount", 0))
    if principal > 0:
        lines.append(f"Основной долг: {_fmt(principal)} руб.")

    # Неустойка
    if penalty_calc.get("success"):
        p = penalty_calc
        lines.append(
            f"Неустойка: {_fmt(p['principal'])} руб. × {p['penalty_rate']}% × "
            f"{p['days']} дн. = {_fmt(p['penalty'])} руб."
        )
        lines.append(f"  (период: с {p['start_date']} по {p['end_date']})")
    else:
        penalty_amount = _to_float(state.get("penalty_amount", 0))
        if penalty_amount > 0:
            lines.append(f"Неустойка: {_fmt(penalty_amount)} руб.")

    # Проценты
    if interest_calc.get("success"):
        i = interest_calc
        lines.append(
            f"Проценты (ст. 395 ГК РФ): {_fmt(i['principal'])} руб. × "
            f"{i['rate'] * 100}% × {i['days']} дн. / 365 = {_fmt(i['interest'])} руб."
        )
        lines.append(f"  (период: с {i['start_date']} по {i['end_date']})")
    else:
        interest_amount = _to_float(state.get("interest_amount", 0))
        if interest_amount > 0:
            lines.append(f"Проценты: {_fmt(interest_amount)} руб.")

    # Моральный вред
    moral = _to_float(state.get("moral_damage", 0))
    if moral > 0:
        lines.append(f"Моральный вред: {_fmt(moral)} руб.")

    # Итого
    lines.append("")
    lines.append(f"ИТОГО цена иска: {_fmt(total_claim)} руб.")
    lines.append("")
    lines.append(f"Государственная пошлина: {_fmt(state_duty)} руб.")

    # Судебные расходы (отдельно)
    expenses = _to_float(state.get("court_expenses", 0))
    if expenses > 0:
        lines.append(f"Судебные расходы: {_fmt(expenses)} руб.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  Госпошлина — суды общей юрисдикции
# ═══════════════════════════════════════════════════════════════


def calc_state_duty_civil(claim: float) -> float:
    """
    Расчёт госпошлины для имущественных исков в судах общей юрисдикции.
    Статья 333.19 п.1 пп.1 НК РФ.

    Args:
        claim: сумма иска в рублях

    Returns:
        размер госпошлины в рублях
    """
    claim = _to_float(claim)

    if claim <= 0:
        raise ValueError(f"Сумма иска должна быть положительной: {claim}")

    if claim <= 100_000:
        duty = 4_000
    elif claim <= 300_000:
        duty = 4_000 + (claim - 100_000) * 0.03
    elif claim <= 500_000:
        duty = 10_000 + (claim - 300_000) * 0.025
    elif claim <= 1_000_000:
        duty = 15_000 + (claim - 500_000) * 0.02
    elif claim <= 3_000_000:
        duty = 25_000 + (claim - 1_000_000) * 0.01
    elif claim <= 8_000_000:
        duty = 45_000 + (claim - 3_000_000) * 0.007
    elif claim <= 24_000_000:
        duty = 80_000 + (claim - 8_000_000) * 0.0035
    elif claim <= 50_000_000:
        duty = 136_000 + (claim - 24_000_000) * 0.003
    elif claim <= 100_000_000:
        duty = 214_000 + (claim - 50_000_000) * 0.002
    else:
        duty = 314_000 + (claim - 100_000_000) * 0.0015
        duty = min(duty, 900_000)  # не более 900 000 рублей

    return duty


# ═══════════════════════════════════════════════════════════════
#  Госпошлина — арбитражные суды
# ═══════════════════════════════════════════════════════════════

def calc_state_duty_arbitration(claim: float) -> float:
    """
    Расчёт госпошлины для имущественных исков в арбитражных судах.
    Статья 333.21 п.1 пп.1 НК РФ.

    Args:
        claim: сумма иска в рублях

    Returns:
        размер госпошлины в рублях
    """
    claim = _to_float(claim)

    if claim <= 0:
        raise ValueError(f"Сумма иска должна быть положительной: {claim}")

    if claim <= 100_000:
        duty = 10_000
    elif claim <= 1_000_000:
        duty = 10_000 + (claim - 100_000) * 0.05
    elif claim <= 10_000_000:
        duty = 55_000 + (claim - 1_000_000) * 0.03
    elif claim <= 50_000_000:
        duty = 325_000 + (claim - 10_000_000) * 0.01
    else:
        duty = 725_000 + (claim - 50_000_000) * 0.005
        duty = min(duty, 10_000_000)  # не более 10 000 000 рублей

    return duty


def calc_state_duty_non_property(
    court_type: str,
    case_category: str = "",
    applicant_type: str = "individual"
) -> float:
    """
    Расчёт госпошлины для неимущественных исков и специальных категорий дел.

    Args:
        court_type: 'civil' или 'arbitration'
        case_category: категория дела
        applicant_type: 'individual' или 'organization'

    Returns:
        размер госпошлины в рублях
    """
    court_type = court_type.lower()
    applicant_type = applicant_type.lower()
    case_category = case_category.lower()

    # Специальные категории
    if case_category == "divorce":
        return 5_000.0

    if case_category == "alimony":
        return 150.0

    if case_category == "alimony_children_and_plaintiff":
        return 300.0

    # Апелляция/кассация
    if case_category.startswith("appeal"):
        return _get_appeal_duty(court_type, applicant_type, case_category)

    # Административные иски
    if case_category.startswith("admin"):
        return _get_admin_duty(court_type, applicant_type, case_category)

    # Банкротство
    if case_category == "bankruptcy":
        if applicant_type == "individual":
            return 10_000.0
        return 100_000.0

    if case_category == "bankruptcy_debtor":
        return 0.0

    # Другие специальные заявления
    special_fees = _get_special_fees(court_type, applicant_type, case_category)
    if special_fees is not None:
        return special_fees

    # Обычные неимущественные иски
    if court_type == "civil":
        duty = 3_000.0 if applicant_type == "individual" else 20_000.0
    elif court_type == "arbitration":
        duty = 15_000.0 if applicant_type == "individual" else 50_000.0
    else:
        raise ValueError(f"Неизвестный тип суда: {court_type}")

    return duty


def _get_appeal_duty(court_type: str, applicant_type: str, category: str) -> float:
    """Госпошлина за апелляцию/кассацию."""
    fees_civil = {
        "appeal": {"individual": 3_000, "organization": 15_000},
        "cassation": {"individual": 5_000, "organization": 20_000},
        "supreme": {"individual": 7_000, "organization": 25_000}
    }

    fees_arbitration = {
        "appeal": {"individual": 10_000, "organization": 30_000},
        "cassation": {"individual": 20_000, "organization": 50_000},
        "supreme": {"individual": 30_000, "organization": 80_000}
    }

    fees = fees_civil if court_type == "civil" else fees_arbitration
    appeal_type = category.replace("appeal_", "") if category.startswith("appeal_") else category

    result = fees.get(appeal_type, {}).get(applicant_type, 0)

    return float(result)


def _get_admin_duty(court_type: str, applicant_type: str, category: str) -> float:
    """Госпошлина по административным искам."""
    if court_type == "civil":
        admin_fees = {
            "admin_normative": {"individual": 4_000, "organization": 20_000},
            "admin_non_normative": {"individual": 3_000, "organization": 15_000},
            "admin_compensation": {"individual": 300, "organization": 6_000},
            "admin_detention": {"individual": 300, "organization": 6_000}
        }
    else:  # arbitration
        admin_fees = {
            "admin_ip_normative": {"individual": 10_000, "organization": 60_000},
            "admin_non_normative": {"individual": 10_000, "organization": 50_000},
            "admin_compensation": {"individual": 300, "organization": 6_000}
        }

    return float(admin_fees.get(category, {}).get(applicant_type, 0))


def _get_special_fees(court_type: str, applicant_type: str, category: str) -> float | None:
    """Другие специальные заявления."""
    special_civil = {
        "special_proceedings": 3_000,
        "succession": {"individual": 2_000, "organization": 15_000},
        "duplicate_writ": 1_500,
        "postponement": 3_000,
        "review_new": 10_000,
        "security": 10_000
    }

    special_arbitration = {
        "legal_facts": 30_000,
        "succession": {"individual": 5_000, "organization": 25_000},
        "duplicate_writ": 10_000,
        "review_new": 30_000,
        "security": 30_000
    }

    fees = special_civil if court_type == "civil" else special_arbitration
    fee = fees.get(category)

    if fee is None:
        return None

    if isinstance(fee, dict):
        return float(fee.get(applicant_type, 0))

    return float(fee)


def calc_court_order_duty(claim_amount: float, court_type: str = "civil") -> float:
    """
    Расчёт госпошлины за судебный приказ.
    50% от пошлины по имущественному иску, но не менее 8000 руб. для арбитража.
    """
    if court_type == "civil":
        base_duty = calc_state_duty_civil(claim_amount)
        return base_duty * 0.5
    else:
        base_duty = calc_state_duty_arbitration(claim_amount)
        return max(base_duty * 0.5, 8_000.0)


def calc_enforcement_duty(decision_amount: float, court_type: str = "civil") -> float:
    """
    Госпошлина за выдачу исполнительных листов.
    30% от госпошлины по имущественному иску.
    """
    if court_type == "civil":
        base_duty = calc_state_duty_civil(decision_amount)
    else:
        base_duty = calc_state_duty_arbitration(decision_amount)

    return base_duty * 0.3


# ═══════════════════════════════════════════════════════════════
#  Утилиты
# ═══════════════════════════════════════════════════════════════

_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y")


def parse_date(s: str) -> date:
    """Парсинг даты из нескольких распространённых форматов."""
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Неизвестный формат даты: «{s}»")


def _days_between(start_str: str, end_str: str) -> int:
    """Расчёт количества дней между двумя датами."""
    d1 = parse_date(start_str)
    d2 = parse_date(end_str)
    delta = (d2 - d1).days
    if delta < 0:
        raise ValueError(f"Начало ({start_str}) позже конца ({end_str})")
    return delta


def _to_float(value: Any) -> float:
    """
    Преобразование значения в float.
    Поддерживает числа, строки с пробелами и запятыми.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        # Убираем все символы кроме цифр, точки и запятой
        cleaned = re.sub(r"[^\d.,]", "", value)

        # Определяем, что используется как разделитель дробной части
        # Если есть и точка и запятая - последний символ это дробный разделитель
        if '.' in cleaned and ',' in cleaned:
            # "1,000.50" - точка дробная, запятая - разделитель тысяч
            if cleaned.rindex('.') > cleaned.rindex(','):
                cleaned = cleaned.replace(',', '')  # убираем запятые (тысячи)
            # "1.000,50" - запятая дробная, точка - разделитель тысяч
            else:
                cleaned = cleaned.replace('.', '').replace(',', '.')
        # Только запятая - либо дробный разделитель, либо тысячи
        elif ',' in cleaned:
            # Если запятая одна и после неё 2 цифры - это дробная часть
            if cleaned.count(',') == 1 and len(cleaned.split(',')[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            # Иначе это разделитель тысяч
            else:
                cleaned = cleaned.replace(',', '')

        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _fmt(value: float) -> str:
    """
    Форматирование суммы: 1 234 567.89

    Args:
        value: числовое значение

    Returns:
        отформатированная строка
    """
    if value == int(value):
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")
