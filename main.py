from __future__ import annotations

import json
import sys

from app.graph import create_graph
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_with_structured_input(data: dict) -> str:
    """Запуск с готовым словарём данных."""
    graph = create_graph()
    initial_state = {
        "input_data": data,
        "x_headers": {}
    }
    result = graph.invoke({"input_data": data})
    return result.get("final_document", result.get("generated_document", ""))


def run_with_raw_text(text: str) -> str:
    """Запуск со свободным текстом."""
    graph = create_graph()
    result = graph.invoke({"raw_input": text})
    return result.get("final_document", result.get("generated_document", ""))


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    """
    Использование:
        python main.py                        — демо с тестовыми данными
        python main.py input.json             — из JSON-файла
        python main.py --text "описание..."   — из свободного текста
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        text = " ".join(sys.argv[2:])
        logger.info("Running with raw text input")
        doc = run_with_raw_text(text)
    elif len(sys.argv) > 1:
        filepath = sys.argv[1]
        logger.info("Running with JSON file: %s", filepath)
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        doc = run_with_structured_input(data)
    else:
        logger.info("Running with demo data")
        doc = run_with_structured_input(_demo_data())

    print("\n" + "=" * 80)
    print(doc)
    print("=" * 80)


def _demo_data() -> dict:
    """Тестовые данные для отладки."""
    return {
        "x_headers": {},
        "plaintiff_info": (
            "Иванов Иван Иванович, 01.01.1976 г.р., "
            "адрес: 123456, г. Москва, ул. Ленина, д. 10, кв. 5, "
            "тел.: +7 (999) 123-45-67, email: ivanov@example.com"
        ),
        "defendant_info": (
            'ООО «Ромашка», ИНН 7701234567, ОГРН 1027700123456, '
            "адрес: 123456, г. Москва, ул. Пушкина, д. 20, офис 100, "
            'в лице генерального директора Петрова П.П.'
        ),
        "third_parties_info": "",
        "court_info": (
            "Тверской районный суд города Москвы, "
            "адрес: 127051, г. Москва, Цветной бульвар, д. 25А"
        ),
        "facts": (
            '15.01.2024 между Ивановым И.И. и ООО «Ромашка» заключён договор '
            "займа № 15/01-2024, по условиям которого Иванов И.И. передал "
            'ООО «Ромашка» денежные средства в размере 500 000 рублей сроком '
            "до 15.07.2024 под 10% годовых. Факт передачи подтверждается "
            "платёжным поручением № 123 от 15.01.2024. "
            "Согласно п. 5.2 договора, в случае просрочки возврата заёмщик "
            "уплачивает неустойку в размере 0,1% от суммы долга за каждый день просрочки. "
            "По состоянию на текущую дату ответчик сумму займа не вернул, "
            "на претензию от 20.07.2024 не ответил."
        ),
        "documents": (
            "1. Договор займа № 15/01-2024 от 15.01.2024\n"
            "2. Платёжное поручение № 123 от 15.01.2024\n"
            "3. Претензия от 20.07.2024 с уведомлением о вручении\n"
            "4. Квитанция об уплате госпошлины"
        ),
        "claims": (
            "Взыскать с ответчика сумму основного долга по договору займа, "
            "неустойку за просрочку возврата, судебные расходы по уплате госпошлины."
        ),
        "pretrial_settlement": (
            "20.07.2024 ответчику направлена претензия с требованием возврата "
            "суммы займа в течение 10 дней. Претензия получена ответчиком "
            "25.07.2024 (уведомление о вручении). Ответа на претензию не последовало."
        ),
        "principal_amount": 500_000,
        "penalty_rate": 0.001,  # 0.1% в день
        "penalty_start_date": "16.07.2024",
        "penalty_end_date": "15.01.2025",
        "moral_damage": 0,
        "court_expenses": 0,
    }


if __name__ == "__main__":
    main()
