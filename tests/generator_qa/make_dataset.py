"""
Датасет для generator_node + qa_node:
готовые состояния claims-агента (intake/case_analysis/calc уже выполнены).
Эталон — чек-лист подстрок, которые должны присутствовать в сгенерированном документе.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.io_utils import write_jsonl


def _civil_consumer(amount: float) -> dict:
    return {
        "case_type": "civil",
        "case_category": "consumer_goods",
        "is_property_dispute": True,
        "classification_data": {
            "case_type": "civil",
            "case_category": "consumer_goods",
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "proceeding_type": "lawsuit",
            "plaintiff_type": "individual",
            "defendant_type": "legal_entity",
            "pretrial_required": False,
        },
        "total_claim": amount,
        "state_duty": 4000.0,
    }


def _arbitration_supply(amount: float) -> dict:
    return {
        "case_type": "arbitration",
        "case_category": "supply",
        "is_property_dispute": True,
        "classification_data": {
            "case_type": "arbitration",
            "case_category": "supply",
            "claim_nature": "property",
            "court_jurisdiction": "arbitration",
            "proceeding_type": "lawsuit",
            "plaintiff_type": "legal_entity",
            "defendant_type": "legal_entity",
            "pretrial_required": True,
        },
        "total_claim": amount,
        "state_duty": 10000.0,
    }


DATASET: list[dict] = [
    # ── Иски (3) ──────────────────────────────────────────────────
    {
        "id": 1,
        "comment": "Иск физлица к магазину — потребительский",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Иванов Иван Иванович, проживает: г. Москва, ул. Тверская, д. 1, кв. 5",
            "defendant_info": "ООО Магазин Электро, ИНН 7700000000, адрес: г. Москва, ул. Ленина, д. 10",
            "facts": "12.03.2026 истец приобрёл холодильник стоимостью 60 000 руб. Через 7 дней холодильник вышел из строя. Продавец отказал в возврате денег.",
            "claims": "Взыскать стоимость товара 60 000 руб., неустойку и компенсацию морального вреда.",
            "principal_amount": 60000,
            "moral_damage": 10000,
            "applicable_laws": "Закон РФ \"О защите прав потребителей\", ст. 18, 23",
            **_civil_consumer(70000),
        },
        "expected": {
            "document_type": "lawsuit",
            "checks": ["Иванов", "Магазин Электро", "60", "холодильник"],
        },
    },
    {
        "id": 2,
        "comment": "Иск ООО к ООО — поставка, арбитраж",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "ООО Альфа, ИНН 7701111111, адрес: г. Москва, ул. Мира, д. 5",
            "defendant_info": "ООО Бета, ИНН 7702222222, адрес: г. Москва, ул. Гагарина, д. 7",
            "facts": "По договору поставки № 12 от 01.03.2026 ООО Альфа поставило ООО Бета оборудование на сумму 1 200 000 руб. Оплата не произведена в срок 30 дней.",
            "claims": "Взыскать задолженность 1 200 000 руб. и неустойку за просрочку оплаты.",
            "principal_amount": 1200000,
            "penalty_amount": 30000,
            "applicable_laws": "ст. 506, 516 ГК РФ",
            **_arbitration_supply(1230000),
        },
        "expected": {
            "document_type": "lawsuit",
            "checks": ["ООО Альфа", "ООО Бета", "1 200 000", "поставк"],
        },
    },
    {
        "id": 3,
        "comment": "Иск работника к работодателю — невыплата зарплаты",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Сидорова Мария Александровна, г. Москва, ул. Профсоюзная, д. 3",
            "defendant_info": "ООО Лотос, ИНН 7703333333, адрес: г. Москва, пр. Мира, д. 100",
            "facts": "С 01.03.2026 по 31.05.2026 работодатель не выплачивал заработную плату по трудовому договору № 7 от 01.01.2025. Общая задолженность 180 000 руб.",
            "claims": "Взыскать задолженность по заработной плате и компенсацию за задержку выплаты.",
            "principal_amount": 180000,
            "applicable_laws": "ст. 21, 22, 236 ТК РФ",
            "case_type": "civil",
            "case_category": "salary",
            "is_property_dispute": True,
            "classification_data": {
                "case_type": "civil",
                "case_category": "salary",
                "claim_nature": "property",
                "court_jurisdiction": "general",
                "proceeding_type": "lawsuit",
                "plaintiff_type": "individual",
                "defendant_type": "legal_entity",
                "pretrial_required": False,
            },
            "total_claim": 180000,
            "state_duty": 0.0,
        },
        "expected": {
            "document_type": "lawsuit",
            "checks": ["Сидорова", "ООО Лотос", "180", "заработн"],
        },
    },
    # ── Претензии (3) ─────────────────────────────────────────────
    {
        "id": 4,
        "comment": "Претензия покупателя продавцу за брак",
        "state": {
            "document_type": "complaint",
            "plaintiff_info": "Романова Юлия Сергеевна, г. Москва, ул. Лесная, д. 12, кв. 3",
            "defendant_info": "ООО Эльдорадо, ИНН 7704444444, г. Москва, ул. Тверская, д. 22",
            "facts": "20.04.2026 куплен телефон стоимостью 45 000 руб. Через 5 дней обнаружен дефект экрана. В возврате отказано.",
            "claims": "Вернуть 45 000 руб. за товар ненадлежащего качества.",
            "principal_amount": 45000,
            "applicable_laws": "Закон РФ \"О защите прав потребителей\", ст. 18",
            "case_type": "civil",
            "case_category": "consumer_goods",
            "is_property_dispute": True,
            "classification_data": {
                "case_type": "civil",
                "case_category": "consumer_goods",
                "claim_nature": "property",
                "court_jurisdiction": "general",
                "proceeding_type": "lawsuit",
                "plaintiff_type": "individual",
                "defendant_type": "legal_entity",
                "pretrial_required": True,
            },
            "complaint_type": "monetary",
            "complaint_sphere": "consumer",
            "complaint_sending_method": "mail",
            "complaint_response_deadline": 10,
        },
        "expected": {
            "document_type": "complaint",
            "checks": ["Романова", "Эльдорадо", "45", "телефон"],
        },
    },
    {
        "id": 5,
        "comment": "Претензия по договору поставки между ЮЛ",
        "state": {
            "document_type": "complaint",
            "plaintiff_info": "ООО Гамма, ИНН 7705555555, г. Москва, ул. Морская, д. 1",
            "defendant_info": "ООО Дельта, ИНН 7706666666, г. Москва, ул. Северная, д. 4",
            "facts": "По договору поставки № 5 от 15.02.2026 ООО Дельта не оплатило поставленный товар в срок. Сумма долга 850 000 руб.",
            "claims": "Оплатить задолженность 850 000 руб. и неустойку за просрочку.",
            "principal_amount": 850000,
            "penalty_amount": 12000,
            "applicable_laws": "ст. 309, 310, 516 ГК РФ",
            "case_type": "arbitration",
            "case_category": "supply",
            "is_property_dispute": True,
            "classification_data": {
                "case_type": "arbitration",
                "case_category": "supply",
                "claim_nature": "property",
                "court_jurisdiction": "arbitration",
                "proceeding_type": "lawsuit",
                "plaintiff_type": "legal_entity",
                "defendant_type": "legal_entity",
                "pretrial_required": True,
            },
            "complaint_type": "monetary",
            "complaint_sphere": "commercial",
            "complaint_sending_method": "mail",
            "complaint_response_deadline": 30,
        },
        "expected": {
            "document_type": "complaint",
            "checks": ["ООО Гамма", "ООО Дельта", "850", "поставк"],
        },
    },
    {
        "id": 6,
        "comment": "Претензия по договору подряда (ремонт)",
        "state": {
            "document_type": "complaint",
            "plaintiff_info": "Орлов Алексей Петрович, г. Москва, ул. Полевая, д. 8, кв. 17",
            "defendant_info": "ИП Кузнецов Сергей Викторович, ОГРНИП 320770000000000",
            "facts": "01.04.2026 заключён договор подряда на ремонт квартиры. Заказчик внёс предоплату 250 000 руб. Подрядчик к работам не приступил.",
            "claims": "Вернуть предоплату 250 000 руб. и расторгнуть договор подряда.",
            "principal_amount": 250000,
            "applicable_laws": "ст. 28, 32 Закона РФ \"О защите прав потребителей\"",
            "case_type": "civil",
            "case_category": "consumer_services",
            "is_property_dispute": True,
            "classification_data": {
                "case_type": "civil",
                "case_category": "consumer_services",
                "claim_nature": "property",
                "court_jurisdiction": "general",
                "proceeding_type": "lawsuit",
                "plaintiff_type": "individual",
                "defendant_type": "ip",
                "pretrial_required": True,
            },
            "complaint_type": "monetary",
            "complaint_sphere": "consumer",
            "complaint_sending_method": "mail",
            "complaint_response_deadline": 10,
        },
        "expected": {
            "document_type": "complaint",
            "checks": ["Орлов", "Кузнецов", "250", "ремонт"],
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
