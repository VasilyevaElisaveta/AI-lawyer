"""
main.py — тест генерации досудебной претензии.

Запуск:
    python main.py

Что проверяется:
    1. Структурированный ввод (input_data dict) → pretenziya.docx
    2. Свободный текст (raw_input str) → печать в консоль
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
#  Входные данные (структурированный вариант)
#  Формат: dict, который агент получает как input_data
# ═══════════════════════════════════════════════════════════════

COMPLAINT_INPUT_STRUCTURED: dict = {
    # ── Тип документа ────────────────────────────────────────
    "document_type": "complaint",          # "lawsuit" | "complaint"

    # ── Стороны ───────────────────────────────────────────────
    "plaintiff_info": (
        "Смирнова Анна Викторовна, "
        "место жительства: г. Москва, ул. Академика Королёва, д. 12, кв. 47, "
        "тел.: +7 (916) 123-45-67, email: smirnova.av@mail.ru"
    ),
    "defendant_info": (
        "ООО «СтройМастер», "
        "адрес: 115054, г. Москва, ул. Дубининская, д. 57, оф. 301, "
        "ИНН 7705123456, ОГРН 1197746123456, "
        "тел.: +7 (495) 987-65-43"
    ),

    # ── Фабула ────────────────────────────────────────────────
    "facts": (
        "15 марта 2025 года между Смирновой А.В. (заказчик) и ООО «СтройМастер» "
        "(подрядчик) был заключён договор подряда № 47/2025 на выполнение ремонтных "
        "работ в квартире по адресу: г. Москва, ул. Академика Королёва, д. 12, кв. 47. "
        "Срок выполнения работ — 60 календарных дней (до 14 мая 2025 года). "
        "Стоимость работ — 380 000 рублей, которые были оплачены в полном объёме "
        "платёжным поручением от 16 марта 2025 года.\n"
        "По состоянию на 01 июня 2025 года работы не завершены: "
        "не выполнена укладка напольного покрытия в двух комнатах, "
        "не завершена отделка санузла, отсутствует финальная покраска стен. "
        "Акт приёма-передачи выполненных работ не подписан. "
        "Подрядчик на звонки отвечает уклончиво, конкретных сроков завершения не называет."
    ),

    # ── Документы ─────────────────────────────────────────────
    "documents": (
        "Договор подряда № 47/2025 от 15.03.2025; "
        "Платёжное поручение № 112 от 16.03.2025 на сумму 380 000 руб.; "
        "Смета на выполнение ремонтных работ от 15.03.2025; "
        "Фотоматериалы, фиксирующие незавершённость работ (от 01.06.2025)"
    ),

    # ── Требования ────────────────────────────────────────────
    "claims": (
        "Завершить ремонтные работы в срок не позднее 20 дней с момента получения "
        "настоящей претензии; "
        "В случае невыполнения требования — вернуть уплаченные денежные средства "
        "в размере 380 000 рублей и выплатить неустойку за просрочку исполнения."
    ),

    # ── Суммы ─────────────────────────────────────────────────
    "principal_amount": 380_000.0,         # сумма по договору
    "penalty_rate": 0.5,                   # % в день (ЗоЗПП ст. 28, п. 5)
    "penalty_start_date": "15.05.2025",    # день, следующий за крайним сроком
    "penalty_end_date": "01.06.2025",      # дата составления претензии

    # ── Параметры претензии ───────────────────────────────────
    "complaint_type": "monetary",          # "monetary" | "non_monetary"
    "complaint_sphere": "consumer",        # "consumer" | "commercial" | "labor" | "other"
    "complaint_sending_method": "mail",    # "in_person" | "mail" | "electronic"
    "complaint_response_deadline": 10,     # дней (ст. 22 ЗоЗПП)
    "complaint_deadline_basis": "п. 5 ст. 28 Закона РФ «О защите прав потребителей»",
}


# ═══════════════════════════════════════════════════════════════
#  Входные данные (вариант свободного текста)
# ═══════════════════════════════════════════════════════════════

COMPLAINT_INPUT_RAW = """\
Хочу написать претензию.

Я, Петров Сергей Николаевич, проживаю: г. Санкт-Петербург, Невский проспект, д. 88, кв. 14,
тел. 8-911-222-33-44.

В интернет-магазине ООО «ТехноМаркет» (ИНН 7812345678, адрес: г. Санкт-Петербург,
ул. Восстания, д. 5) 10 апреля 2025 года купил ноутбук Lenovo IdeaPad за 89 000 рублей
(чек № 00445 от 10.04.2025). Через 3 недели экран начал мигать и появились горизонтальные
полосы — явный производственный дефект. 05 мая 2025 года сдал ноутбук в сервисный центр
магазина для диагностики, получил акт приёма № СЦ-2025-0512.

По состоянию на 02 июня 2025 года ни ремонта, ни ответа нет — прошло уже 28 дней.
По закону о защите прав потребителей срок ремонта — не более 45 дней, но магазин молчит.

Хочу потребовать либо замены ноутбука, либо возврата 89 000 рублей,
а также неустойку за каждый день просрочки.
"""


# ═══════════════════════════════════════════════════════════════
#  Вспомогательные функции
# ═══════════════════════════════════════════════════════════════

def save_docx(base64_str: str, filename: str) -> Path:
    """Декодирует base64 и сохраняет DOCX-файл."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / filename
    filepath.write_bytes(base64.b64decode(base64_str))
    return filepath


def print_separator(title: str) -> None:
    width = 60
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


def print_response(result: dict, label: str) -> None:
    """Красиво выводит результат агента."""
    print_separator(label)
    print(f"  handled_by_agent : {result.get('handled_by_agent')}")
    print(f"  document_created : {result.get('document_created')}")
    print(f"  document_type    : {result.get('document_type', '—')}")
    print(f"  status           : {result.get('status', '—')}")

    reply = result.get("reply", "")
    if result.get("document_created"):
        # reply — это base64 DOCX
        print(f"  reply            : <base64 DOCX, {len(reply)} символов>")
        if result.get("metadata"):
            meta = result["metadata"]
            print(f"  metadata.plaintiff : {meta.get('plaintiff', '')[:60]}")
            print(f"  metadata.defendant : {meta.get('defendant', '')[:60]}")
            print(f"  metadata.total_claim : {meta.get('total_claim', 0)}")
    else:
        # reply — текст (ошибка или сообщение)
        print(f"  reply (text)     :\n{reply}")


# ═══════════════════════════════════════════════════════════════
#  Основной тест
# ═══════════════════════════════════════════════════════════════

async def test_structured_input() -> None:
    """
    Тест 1: структурированный ввод → DOCX-претензия.
    Агент получает готовый dict через поле input_data.
    """
    from claims_agent.graph import ClaimsAgent

    print_separator("ТЕСТ 1: структурированный ввод (pretenziya_stroika.docx)")

    agent = ClaimsAgent()

    # Агент принимает либо JSON-строку, либо dict в поле input_data.
    # Самый простой способ — передать JSON-строку: агент сам распарсит.
    message = json.dumps(COMPLAINT_INPUT_STRUCTURED, ensure_ascii=False)

    result = await agent.process_user_message(
        user_message=message,
        thread_id="test-complaint-structured-001",
        document_type="complaint",   # дублируем явно (можно не указывать — есть в JSON)
    )

    print_response(result, "Результат теста 1")

    if result.get("document_created") and result.get("reply"):
        path = save_docx(result["reply"], "pretenziya_stroika.docx")
        print(f"\n  ✓ DOCX сохранён: {path.resolve()}")
    else:
        print("\n  ✗ Документ не создан — смотри поле 'reply' выше")


async def test_raw_input() -> None:
    """
    Тест 2: свободный текст → LLM-извлечение → DOCX-претензия.
    Агент сам извлекает данные из текста через LLM (intake_node).
    """
    from claims_agent.graph import ClaimsAgent

    print_separator("ТЕСТ 2: свободный текст (pretenziya_noutbuk.docx)")

    agent = ClaimsAgent()

    result = await agent.process_user_message(
        user_message=COMPLAINT_INPUT_RAW,
        thread_id="test-complaint-raw-002",
        document_type="complaint",
    )

    print_response(result, "Результат теста 2")

    if result.get("document_created") and result.get("reply"):
        path = save_docx(result["reply"], "pretenziya_noutbuk.docx")
        print(f"\n  ✓ DOCX сохранён: {path.resolve()}")
    else:
        print("\n  ✗ Документ не создан — смотри поле 'reply' выше")


async def test_lawsuit_still_works() -> None:
    """
    Тест 3: убеждаемся, что исковые заявления не сломались.
    Минимальный структурированный ввод.
    """
    from claims_agent.graph import ClaimsAgent

    print_separator("ТЕСТ 3: регрессия — исковое заявление (isk_dolg.docx)")

    agent = ClaimsAgent()

    lawsuit_input = {
        "document_type": "lawsuit",
        "plaintiff_info": (
            "Коваленко Дмитрий Алексеевич, "
            "адрес: г. Екатеринбург, ул. Ленина, д. 5, кв. 3, "
            "тел.: +7 (912) 000-11-22"
        ),
        "defendant_info": (
            "Захаров Илья Петрович, "
            "адрес: г. Екатеринбург, ул. Мира, д. 10, кв. 55"
        ),
        "facts": (
            "01 января 2024 года Коваленко Д.А. передал Захарову И.П. денежные "
            "средства в сумме 200 000 рублей по договору займа № 1/2024 сроком "
            "возврата до 01 июля 2024 года. По истечении срока Захаров И.П. "
            "денежные средства не вернул, на контакт не выходит."
        ),
        "documents": (
            "Договор займа № 1/2024 от 01.01.2024; "
            "Расписка о получении денежных средств от 01.01.2024"
        ),
        "claims": (
            "Взыскать с ответчика сумму основного долга 200 000 рублей, "
            "проценты по ст. 395 ГК РФ, судебные расходы."
        ),
        "principal_amount": 200_000.0,
        "interest_start_date": "02.07.2024",
        "interest_end_date": "01.06.2025",
        "cbr_key_rate": 0.16,
        "pretrial_settlement": "Претензия направлена 05.07.2024, ответ не получен.",
    }

    message = json.dumps(lawsuit_input, ensure_ascii=False)
    result = await agent.process_user_message(
        user_message=message,
        thread_id="test-lawsuit-regression-003",
    )

    print_response(result, "Результат теста 3")

    if result.get("document_created") and result.get("reply"):
        path = save_docx(result["reply"], "isk_dolg.docx")
        print(f"\n  ✓ DOCX сохранён: {path.resolve()}")
    else:
        print("\n  ✗ Документ не создан — смотри поле 'reply' выше")


async def main() -> None:
    await test_structured_input()
    await test_raw_input()
    await test_lawsuit_still_works()

    print_separator("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("  Файлы сохранены в ./output/\n")


if __name__ == "__main__":
    asyncio.run(main())
