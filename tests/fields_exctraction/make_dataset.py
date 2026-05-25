"""
Датасет для тестирования intake (извлечение полей из сообщения пользователя).
25 кейсов: структурированные, свободные, минимальные, с шумом.
`expected_fields` — поля, которые модель должна заполнить (значения сравниваются нечётко).
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.io_utils import write_jsonl


DATASET: list[dict] = [
    # ── Структурированные (8) ─────────────────────────────────────
    {
        "id": 1,
        "raw_input": (
            "Истец: Калашников В.С., Ответчик: Колотыгин Д.В., "
            "Требования: вернуть деньги за покупку, "
            "Сумма основного требования: 500000 рублей."
        ),
        "document_type": "lawsuit",
        "difficulty": "easy",
        "expected_fields": {
            "plaintiff_info": "Калашников В.С.",
            "defendant_info": "Колотыгин Д.В.",
            "claims": "вернуть деньги за покупку",
            "principal_amount": 500000,
        },
    },
    {
        "id": 2,
        "raw_input": (
            "Истец: Иванов И.И., Ответчик: ООО Ромашка, "
            "Требования: взыскать задолженность, Сумма: 120 500 руб."
        ),
        "document_type": "lawsuit",
        "difficulty": "easy",
        "expected_fields": {
            "plaintiff_info": "Иванов И.И.",
            "defendant_info": "ООО Ромашка",
            "claims": "взыскать задолженность",
            "principal_amount": 120500,
        },
    },
    {
        "id": 3,
        "raw_input": (
            "Истец: Петрова Анна Сергеевна, Ответчик: ИП Сидоров А.А., "
            "Требования: расторгнуть договор оказания услуг и вернуть оплату, "
            "Сумма: 75000 рублей."
        ),
        "document_type": "lawsuit",
        "difficulty": "easy",
        "expected_fields": {
            "plaintiff_info": "Петрова Анна Сергеевна",
            "defendant_info": "ИП Сидоров А.А.",
            "claims": "расторгнуть договор оказания услуг и вернуть оплату",
            "principal_amount": 75000,
        },
    },
    {
        "id": 4,
        "raw_input": (
            "Отправитель: ООО Альфа, Получатель: ООО Бета, "
            "Требования: оплатить задолженность по договору поставки № 12 от 15.01.2026"
        ),
        "document_type": "complaint",
        "difficulty": "easy",
        "expected_fields": {
            "plaintiff_info": "ООО Альфа",
            "defendant_info": "ООО Бета",
            "claims": "оплатить задолженность по договору поставки",
        },
    },
    {
        "id": 5,
        "raw_input": (
            "Истец: Смирнов А.А., Ответчик: ООО ЖилКомфорт, "
            "Требования: возместить ущерб от залива квартиры, "
            "Сумма: 200000 рублей, Моральный вред: 50000 руб."
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Смирнов А.А.",
            "defendant_info": "ООО ЖилКомфорт",
            "claims": "возместить ущерб от залива квартиры",
            "principal_amount": 200000,
            "moral_damage": 50000,
        },
    },
    {
        "id": 6,
        "raw_input": (
            "Истец Орлов Д.В., Ответчик ИП Кузнецов, требования вернуть аванс 80 000 руб., "
            "также проценты по 395 ГК"
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Орлов Д.В.",
            "defendant_info": "ИП Кузнецов",
            "claims": "вернуть аванс",
            "principal_amount": 80000,
        },
    },
    {
        "id": 7,
        "raw_input": (
            "Истец: Беляева М.К., Ответчик: ПАО Энергосбыт, "
            "Требования: пересчитать задолженность, признать незаконным начисление, "
            "Сумма основного требования: 0 (неимущественный спор)"
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Беляева М.К.",
            "defendant_info": "ПАО Энергосбыт",
            "claims": "пересчитать задолженность",
        },
    },
    {
        "id": 8,
        "raw_input": (
            "Истец: Захаров П.П., Ответчик: ООО Стройинвест, "
            "Требования: устранить недостатки выполненных работ по договору подряда, "
            "Сумма: 350000 руб., Неустойка: 20000 руб."
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Захаров П.П.",
            "defendant_info": "ООО Стройинвест",
            "claims": "устранить недостатки выполненных работ",
            "principal_amount": 350000,
            "penalty_amount": 20000,
        },
    },
    # ── Свободный текст (8) ───────────────────────────────────────
    {
        "id": 9,
        "raw_input": (
            "Я Иван Иванов купил холодильник в магазине ООО Электро. "
            "Холодильник сломался через неделю, магазин отказывается возвращать деньги. "
            "Стоимость 60 000 рублей. Хочу подать на возврат денег и неустойку."
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Иван Иванов",
            "defendant_info": "ООО Электро",
            "claims": "возврат денег",
            "principal_amount": 60000,
        },
    },
    {
        "id": 10,
        "raw_input": (
            "ООО Альфа поставило ООО Бета оборудование по договору № 7 от 01.03.2026 "
            "на сумму 1 200 000 руб. Бета не оплатила в срок. Требуем оплатить долг и пени."
        ),
        "document_type": "lawsuit",
        "difficulty": "hard",
        "expected_fields": {
            "plaintiff_info": "ООО Альфа",
            "defendant_info": "ООО Бета",
            "claims": "оплатить долг",
            "principal_amount": 1200000,
        },
    },
    {
        "id": 11,
        "raw_input": (
            "Меня зовут Мария Сидорова. Работала в ООО Лотос, уволили без объяснений. "
            "Зарплату за два месяца не выплатили — около 90 000 рублей. "
            "Хочу взыскать долг по зарплате и компенсацию."
        ),
        "document_type": "lawsuit",
        "difficulty": "hard",
        "expected_fields": {
            "plaintiff_info": "Мария Сидорова",
            "defendant_info": "ООО Лотос",
            "claims": "взыскать долг по зарплате",
            "principal_amount": 90000,
        },
    },
    {
        "id": 12,
        "raw_input": (
            "Я Алексей Орлов, заключил договор с ИП Кузнецов на ремонт квартиры. "
            "Заплатил 250 000 рублей предоплаты, работы не выполнены, на связь не выходит. "
            "Хочу вернуть деньги и неустойку."
        ),
        "document_type": "complaint",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Алексей Орлов",
            "defendant_info": "ИП Кузнецов",
            "claims": "вернуть деньги",
            "principal_amount": 250000,
        },
    },
    {
        "id": 13,
        "raw_input": (
            "Соседи сверху затопили квартиру. Я — Николай Громов, виновник — Петренко Сергей. "
            "Ущерб по оценке 180 000 рублей. Прошу возместить ущерб."
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Николай Громов",
            "defendant_info": "Петренко Сергей",
            "claims": "возместить ущерб",
            "principal_amount": 180000,
        },
    },
    {
        "id": 14,
        "raw_input": (
            "В магазине Эльдорадо мне продали телефон с дефектом. "
            "Я — Юлия Романова. Цена 45 000 руб. Прошу обмена или возврата."
        ),
        "document_type": "complaint",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Юлия Романова",
            "defendant_info": "Эльдорадо",
            "claims": "обмен или возврат",
            "principal_amount": 45000,
        },
    },
    {
        "id": 15,
        "raw_input": (
            "ООО Сигма арендует помещение у ИП Власова, не платит арендную плату с января. "
            "Долг 360 000 руб. Хотим взыскать задолженность и проценты."
        ),
        "document_type": "lawsuit",
        "difficulty": "hard",
        "expected_fields": {
            "plaintiff_info": "ИП Власова",
            "defendant_info": "ООО Сигма",
            "claims": "взыскать задолженность",
            "principal_amount": 360000,
        },
    },
    {
        "id": 16,
        "raw_input": (
            "Я подал заявление о возврате брака, продавец проигнорировал. "
            "Покупатель — Тимур Шакиров, продавец — ООО Маркет 24. "
            "Цена товара 30 000 руб."
        ),
        "document_type": "complaint",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Тимур Шакиров",
            "defendant_info": "ООО Маркет 24",
            "principal_amount": 30000,
        },
    },
    # ── Минимальные (5) ───────────────────────────────────────────
    {
        "id": 17,
        "raw_input": "Верни Колотыгину 500 000",
        "document_type": "lawsuit",
        "difficulty": "hard",
        "expected_fields": {
            "defendant_info": "Колотыгин",
            "principal_amount": 500000,
        },
    },
    {
        "id": 18,
        "raw_input": "Создай мне иск",
        "document_type": "lawsuit",
        "difficulty": "easy",
        "expected_fields": {},
    },
    {
        "id": 19,
        "raw_input": "Хочу взыскать с ООО Альфа 100 000 рублей",
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "defendant_info": "ООО Альфа",
            "principal_amount": 100000,
            "claims": "взыскать",
        },
    },
    {
        "id": 20,
        "raw_input": "Иванов хочет претензию к ООО Ромашка",
        "document_type": "complaint",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Иванов",
            "defendant_info": "ООО Ромашка",
        },
    },
    {
        "id": 21,
        "raw_input": "Требую вернуть 25 тысяч за услугу",
        "document_type": "complaint",
        "difficulty": "hard",
        "expected_fields": {
            "principal_amount": 25000,
            "claims": "вернуть",
        },
    },
    # ── С шумом / опечатками (4) ──────────────────────────────────
    {
        "id": 22,
        "raw_input": (
            "ну короче ваще, истец у нас Иванов А.А., атветчик ООО Ромашка, "
            "хочу взыскать 150 000 рублей долга по договору"
        ),
        "document_type": "lawsuit",
        "difficulty": "hard",
        "expected_fields": {
            "plaintiff_info": "Иванов А.А.",
            "defendant_info": "ООО Ромашка",
            "principal_amount": 150000,
        },
    },
    {
        "id": 23,
        "raw_input": (
            "Привет!!! Помоги пожалуйста, я Ольга Сергеева хочу составить иск к компании "
            "Аква-Сервис, они мне поставили бракованный кулер за 45000, надо вернуть деньги."
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Ольга Сергеева",
            "defendant_info": "Аква-Сервис",
            "claims": "вернуть деньги",
            "principal_amount": 45000,
        },
    },
    {
        "id": 24,
        "raw_input": (
            "Истец-Семёнов К.К., ответчик-ООО ТехноПлюс, "
            "сумма основного требования - 80.000 рублей, требование - расторжение договора"
        ),
        "document_type": "lawsuit",
        "difficulty": "medium",
        "expected_fields": {
            "plaintiff_info": "Семёнов К.К.",
            "defendant_info": "ООО ТехноПлюс",
            "claims": "расторжение договора",
            "principal_amount": 80000,
        },
    },
    {
        "id": 25,
        "raw_input": (
            "Меня зовут Ким А.В., работаю в ИП Зайцев, "
            "не выплатили зарплату за апрель и май, итого 110 000 рублей."
        ),
        "document_type": "lawsuit",
        "difficulty": "hard",
        "expected_fields": {
            "plaintiff_info": "Ким А.В.",
            "defendant_info": "ИП Зайцев",
            "principal_amount": 110000,
        },
    },
]


def main(out_path: str) -> None:
    write_jsonl(out_path, DATASET)
    print(f"Saved {len(DATASET)} examples → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "dataset.jsonl"),
    )
    args = parser.parse_args()
    main(args.out)
