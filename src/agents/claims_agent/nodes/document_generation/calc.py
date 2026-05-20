"""
Модуль расчётов.
"""
import os
from datetime import date, datetime
from typing import Any

from logger import LoggerFactory

from ...services.calculator import calculate_state_duty_from_state
from ...services.calculator.fee_calculator import DutyResult
from ...state import ClaimsAgentState


logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

# ═══════════════════════════════════════════════════════════════
#  Публичный узел графа
# ═══════════════════════════════════════════════════════════════


def calculator_node(state: ClaimsAgentState) -> dict[str, Any]:
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
        # Расчёт госпошлины (CourtDutyCalculator)
        duty_result = calculate_state_duty_from_state(state)
        state_duty = duty_result.amount

        # Расчёт неустойки (если есть параметры)
        penalty_calc = _calculate_penalty(state)

        # Расчёт процентов (если есть параметры)
        interest_calc = _calculate_interest(state)

        # Итоговая сумма иска
        total_claim = _calculate_total_claim(state, penalty_calc, interest_calc)

        # Формируем детальный расчёт для документа
        calculation_details = _format_calculation_details(
            state, duty_result, penalty_calc, interest_calc, total_claim
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


def _calculate_penalty(state: ClaimsAgentState) -> dict[str, Any]:
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


def _calculate_interest(state: ClaimsAgentState) -> dict[str, Any]:
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
    state: ClaimsAgentState,
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
    state: ClaimsAgentState,
    duty_result: DutyResult,
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
    lines.append("Государственная пошлина:")
    if duty_result.is_exempt:
        lines.append(f"  Освобождение: {duty_result.exemption_details}")
        lines.append("  К уплате: 0 руб.")
    else:
        if duty_result.exemption_details:
            lines.append(f"  Льгота: {duty_result.exemption_details}")
        for detail_line in duty_result.calculation_details.splitlines():
            lines.append(f"  {detail_line}")
        lines.append(f"  К уплате: {_fmt(duty_result.amount)} руб.")
    for warning in duty_result.warnings:
        lines.append(f"  ⚠ {warning}")

    # Судебные расходы (отдельно)
    expenses = _to_float(state.get("court_expenses", 0))
    if expenses > 0:
        lines.append(f"Судебные расходы: {_fmt(expenses)} руб.")

    return "\n".join(lines)


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