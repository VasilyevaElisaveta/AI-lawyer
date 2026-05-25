"""
Датасет для проверки claims_agent.classification_node (юридическая классификация).
Эталон по полям case_type, claim_nature, court_jurisdiction, плюс набор допустимых
значений case_category. Используется состояние claims-агента (plaintiff/facts/claims/...).
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.io_utils import write_jsonl


DATASET: list[dict] = [
    {
        "id": 1,
        "comment": "Потребительский спор: возврат денег за товар",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Иванов И.И., физическое лицо",
            "defendant_info": "ООО Магазин",
            "facts": "В магазине куплен бракованный холодильник за 60 000 руб. Продавец отказал в возврате.",
            "claims": "Взыскать стоимость товара и неустойку",
            "principal_amount": 60000,
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "acceptable_categories": ["consumer_goods", "consumer_services"],
        },
    },
    {
        "id": 2,
        "comment": "Арбитражный спор между двумя ЮЛ по договору поставки",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "ООО Альфа, юридическое лицо",
            "defendant_info": "ООО Бета, юридическое лицо",
            "facts": "По договору поставки № 12 от 01.03.2026 ответчик не оплатил поставленный товар.",
            "claims": "Взыскать задолженность и неустойку",
            "principal_amount": 1_200_000,
        },
        "expected": {
            "case_type": "arbitration",
            "claim_nature": "property",
            "court_jurisdiction": "arbitration",
            "acceptable_categories": ["supply", "debt_collection"],
        },
    },
    {
        "id": 3,
        "comment": "Трудовой спор: взыскание зарплаты",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Сидорова М.А., физлицо",
            "defendant_info": "ООО Лотос, работодатель",
            "facts": "С марта по май 2026 года работодатель не выплачивал зарплату.",
            "claims": "Взыскать задолженность по заработной плате",
            "principal_amount": 180_000,
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "acceptable_categories": ["salary", "labor_other"],
        },
    },
    {
        "id": 4,
        "comment": "Трудовой спор: восстановление на работе",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Петров А.А., физлицо",
            "defendant_info": "ООО Гамма",
            "facts": "Уволен по сокращению с нарушением процедуры 01.04.2026.",
            "claims": "Восстановить на работе, взыскать средний заработок за время вынужденного прогула",
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "mixed",
            "court_jurisdiction": "general",
            "acceptable_categories": ["dismissal", "labor_other"],
        },
    },
    {
        "id": 5,
        "comment": "Развод без имущества",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Иванова И.А., физлицо",
            "defendant_info": "Иванов И.И., физлицо",
            "facts": "Брак фактически прекращён, общих несовершеннолетних детей нет.",
            "claims": "Расторгнуть брак",
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "non_property",
            "court_jurisdiction": "magistrate",
            "acceptable_categories": ["family"],
        },
    },
    {
        "id": 6,
        "comment": "Взыскание алиментов на ребёнка",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Иванова И.А., мать ребёнка",
            "defendant_info": "Иванов И.И., отец ребёнка",
            "facts": "Ответчик не участвует в содержании несовершеннолетней дочери 2018 г.р.",
            "claims": "Взыскать алименты в размере 1/4 части заработка",
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "property",
            "court_jurisdiction": "magistrate",
            "acceptable_categories": ["family"],
        },
    },
    {
        "id": 7,
        "comment": "Залив квартиры (деликт)",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Громов Н.Н., физлицо",
            "defendant_info": "Петренко С.С., физлицо",
            "facts": "Сосед сверху затопил квартиру 10.04.2026. Стоимость ремонта 180 000 руб.",
            "claims": "Возместить ущерб от залива квартиры",
            "principal_amount": 180000,
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "acceptable_categories": ["tort", "property_dispute"],
        },
    },
    {
        "id": 8,
        "comment": "Аренда между ЮЛ — арбитраж",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "ИП Власова, арендодатель",
            "defendant_info": "ООО Сигма, арендатор",
            "facts": "С января 2026 ООО Сигма не платит арендную плату по договору № 5.",
            "claims": "Взыскать задолженность по аренде и проценты",
            "principal_amount": 360_000,
        },
        "expected": {
            "case_type": "arbitration",
            "claim_nature": "property",
            "court_jurisdiction": "arbitration",
            "acceptable_categories": ["lease", "debt_collection"],
        },
    },
    {
        "id": 9,
        "comment": "Жилищный спор: вселение",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Орлов Д.В., физлицо",
            "defendant_info": "Орлова О.Д., физлицо",
            "facts": "Бывшая супруга препятствует вселению в совместно нажитую квартиру.",
            "claims": "Вселить и обязать не чинить препятствий в пользовании жильём",
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "non_property",
            "court_jurisdiction": "general",
            "acceptable_categories": ["housing", "family"],
        },
    },
    {
        "id": 10,
        "comment": "Услуги: возврат предоплаты",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Алексей Орлов, физлицо",
            "defendant_info": "ИП Кузнецов, исполнитель",
            "facts": "Заказчик перечислил 250 000 руб. за ремонт квартиры. Подрядчик работы не выполнил.",
            "claims": "Взыскать предоплату и неустойку",
            "principal_amount": 250000,
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "acceptable_categories": ["consumer_services", "services"],
        },
    },
    {
        "id": 11,
        "comment": "Защита деловой репутации (ЮЛ)",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "ООО ТехноПлюс",
            "defendant_info": "ООО МедиаПлюс",
            "facts": "Ответчик распространил недостоверные сведения о деятельности истца на сайте.",
            "claims": "Опровергнуть сведения и удалить публикацию",
        },
        "expected": {
            "case_type": "arbitration",
            "claim_nature": "non_property",
            "court_jurisdiction": "arbitration",
            "acceptable_categories": ["other", "ip_copyright", "ip_trademark"],
        },
    },
    {
        "id": 12,
        "comment": "Неосновательное обогащение между физлицами",
        "state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Семёнов К.К., физлицо",
            "defendant_info": "Захарова Н.Н., физлицо",
            "facts": "По ошибке переведено 120 000 руб. на счёт ответчика. Возврат добровольно не произведён.",
            "claims": "Взыскать неосновательное обогащение",
            "principal_amount": 120_000,
        },
        "expected": {
            "case_type": "civil",
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "acceptable_categories": ["unjust_enrichment", "debt_collection"],
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
