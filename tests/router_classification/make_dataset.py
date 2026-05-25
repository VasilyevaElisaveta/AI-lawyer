"""
Датасет для теста router-classification: 25 запросов с эталонной категорией.
Категории: claim, pretrial_claim, general_question, contract.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.io_utils import write_jsonl


DATASET: list[dict] = [
    # ── claim: явные (5) ──────────────────────────────────────────
    {"id": 1, "raw_input": "Составь исковое заявление в суд", "category": "claim", "difficulty": "easy"},
    {"id": 2, "raw_input": "Помоги подать иск к работодателю о невыплате зарплаты", "category": "claim", "difficulty": "easy"},
    {"id": 3, "raw_input": "Нужно подготовить иск против ООО Ромашка", "category": "claim", "difficulty": "easy"},
    {"id": 4, "raw_input": "Хочу обратиться в районный суд с исковым заявлением", "category": "claim", "difficulty": "easy"},
    {"id": 5, "raw_input": "Подайте от моего имени иск о расторжении договора", "category": "claim", "difficulty": "easy"},
    # ── claim: неявные (3) ────────────────────────────────────────
    {"id": 6, "raw_input": "Хочу взыскать долг через суд с физического лица", "category": "claim", "difficulty": "medium"},
    {"id": 7, "raw_input": "Меня уволили незаконно, готов идти до конца и судиться", "category": "claim", "difficulty": "medium"},
    {"id": 8, "raw_input": "Сосед затопил квартиру, ущерб 200 тысяч, добровольно не платит — хочу через суд", "category": "claim", "difficulty": "medium"},
    # ── pretrial_claim: явные (5) ─────────────────────────────────
    {"id": 9, "raw_input": "Составь претензию продавцу за бракованный товар", "category": "pretrial_claim", "difficulty": "easy"},
    {"id": 10, "raw_input": "Нужна досудебная претензия о возврате денежных средств", "category": "pretrial_claim", "difficulty": "easy"},
    {"id": 11, "raw_input": "Напиши претензию в управляющую компанию", "category": "pretrial_claim", "difficulty": "easy"},
    {"id": 12, "raw_input": "Подготовь претензию по договору поставки", "category": "pretrial_claim", "difficulty": "easy"},
    {"id": 13, "raw_input": "Хочу направить претензию банку о возврате комиссии", "category": "pretrial_claim", "difficulty": "easy"},
    # ── pretrial_claim: неявные (2) ───────────────────────────────
    {"id": 14, "raw_input": "Магазин не возвращает деньги, надо потребовать письменно до суда", "category": "pretrial_claim", "difficulty": "medium"},
    {"id": 15, "raw_input": "Хочу досудебно урегулировать спор с подрядчиком", "category": "pretrial_claim", "difficulty": "medium"},
    # ── general_question (6) ──────────────────────────────────────
    {"id": 16, "raw_input": "Что такое срок исковой давности?", "category": "general_question", "difficulty": "easy"},
    {"id": 17, "raw_input": "Чем отличается претензия от иска?", "category": "general_question", "difficulty": "easy"},
    {"id": 18, "raw_input": "Как рассчитывается госпошлина в суд общей юрисдикции?", "category": "general_question", "difficulty": "easy"},
    {"id": 19, "raw_input": "Какие статьи ГК регулируют возврат товара ненадлежащего качества?", "category": "general_question", "difficulty": "medium"},
    {"id": 20, "raw_input": "Привет, чем ты можешь помочь?", "category": "general_question", "difficulty": "easy"},
    {"id": 21, "raw_input": "Подскажи, обязательно ли соблюдать претензионный порядок", "category": "general_question", "difficulty": "hard"},
    # ── contract (2) ──────────────────────────────────────────────
    {"id": 22, "raw_input": "Составь договор аренды квартиры на 11 месяцев", "category": "contract", "difficulty": "easy"},
    {"id": 23, "raw_input": "Нужен договор оказания юридических услуг между ИП и ООО", "category": "contract", "difficulty": "easy"},
    # ── двусмысленные (2) ─────────────────────────────────────────
    {"id": 24, "raw_input": "Хочу вернуть деньги за купленный товар", "category": "pretrial_claim", "difficulty": "hard"},
    {"id": 25, "raw_input": "Решить спор с продавцом", "category": "pretrial_claim", "difficulty": "hard"},
]


def main(out_path: str) -> None:
    write_jsonl(out_path, DATASET)
    print(f"Saved {len(DATASET)} examples → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "dataset.jsonl"),
        help="Путь до файла датасета",
    )
    args = parser.parse_args()
    main(args.out)
