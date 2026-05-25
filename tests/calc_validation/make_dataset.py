"""
Табличный датасет для детерминированных узлов calculator_node и validation_node.
Без LLM. Каждый пример имеет поле `task` ∈ {"calc", "validation"}.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.io_utils import write_jsonl


def _civil_property(amount: float) -> dict:
    return {
        "case_type": "civil",
        "is_property_dispute": True,
        "classification_data": {
            "claim_nature": "property",
            "court_jurisdiction": "general",
            "plaintiff_type": "individual",
            "case_category": "other",
        },
        "principal_amount": amount,
    }


def _arbitration_property(amount: float) -> dict:
    return {
        "case_type": "arbitration",
        "is_property_dispute": True,
        "classification_data": {
            "claim_nature": "property",
            "court_jurisdiction": "arbitration",
            "plaintiff_type": "legal_entity",
            "case_category": "other",
        },
        "principal_amount": amount,
    }


# Эталоны рассчитаны по ст. 333.19 / 333.21 НК РФ (актуальные ставки).
CALC_CASES = [
    {"id": 1, "task": "calc", "comment": "ОЮ имущ. 50 000 → 4 000", "state": _civil_property(50_000), "expected": {"state_duty": 4_000, "total_claim": 50_000}},
    {"id": 2, "task": "calc", "comment": "ОЮ имущ. 100 000 → 4 000", "state": _civil_property(100_000), "expected": {"state_duty": 4_000, "total_claim": 100_000}},
    {"id": 3, "task": "calc", "comment": "ОЮ имущ. 200 000 → 7 000", "state": _civil_property(200_000), "expected": {"state_duty": 7_000, "total_claim": 200_000}},
    {"id": 4, "task": "calc", "comment": "ОЮ имущ. 300 000 → 10 000", "state": _civil_property(300_000), "expected": {"state_duty": 10_000, "total_claim": 300_000}},
    {"id": 5, "task": "calc", "comment": "ОЮ имущ. 500 000 → 15 000", "state": _civil_property(500_000), "expected": {"state_duty": 15_000, "total_claim": 500_000}},
    {"id": 6, "task": "calc", "comment": "ОЮ имущ. 1 000 000 → 25 000", "state": _civil_property(1_000_000), "expected": {"state_duty": 25_000, "total_claim": 1_000_000}},
    {"id": 7, "task": "calc", "comment": "ОЮ имущ. 3 000 000 → 45 000", "state": _civil_property(3_000_000), "expected": {"state_duty": 45_000, "total_claim": 3_000_000}},
    {"id": 8, "task": "calc", "comment": "ОЮ имущ. 8 000 000 → 80 000", "state": _civil_property(8_000_000), "expected": {"state_duty": 80_000, "total_claim": 8_000_000}},
    {"id": 9, "task": "calc", "comment": "Арбитраж имущ. 100 000 → 10 000", "state": _arbitration_property(100_000), "expected": {"state_duty": 10_000, "total_claim": 100_000}},
    {"id": 10, "task": "calc", "comment": "Арбитраж имущ. 200 000 → 15 000", "state": _arbitration_property(200_000), "expected": {"state_duty": 15_000, "total_claim": 200_000}},
    {"id": 11, "task": "calc", "comment": "Арбитраж имущ. 1 000 000 → 55 000", "state": _arbitration_property(1_000_000), "expected": {"state_duty": 55_000, "total_claim": 1_000_000}},
    {"id": 12, "task": "calc", "comment": "Арбитраж имущ. 10 000 000 → 325 000", "state": _arbitration_property(10_000_000), "expected": {"state_duty": 325_000, "total_claim": 10_000_000}},
]


_FULL_LAWSUIT = {
    "document_type": "lawsuit",
    "plaintiff_info": "Иванов И.И.",
    "defendant_info": "ООО Ромашка",
    "facts": "С 01.01.2026 ответчик не возвращает долг по договору займа.",
    "claims": "Взыскать сумму долга и проценты",
    "principal_amount": 200_000,
}


def _modify(base: dict, **changes) -> dict:
    new = dict(base)
    for key, value in changes.items():
        if value is _DELETE:
            new.pop(key, None)
        else:
            new[key] = value
    return new


class _Delete: ...
_DELETE = _Delete()


VALIDATION_CASES = [
    {
        "id": 13, "task": "validation",
        "comment": "Полный иск → is_valid=True",
        "state": dict(_FULL_LAWSUIT),
        "expected": {"is_valid": True, "must_contain_errors": []},
    },
    {
        "id": 14, "task": "validation",
        "comment": "Нет истца",
        "state": _modify(_FULL_LAWSUIT, plaintiff_info=""),
        "expected": {"is_valid": False, "must_contain_errors": ["отправител"]},
    },
    {
        "id": 15, "task": "validation",
        "comment": "Нет ответчика",
        "state": _modify(_FULL_LAWSUIT, defendant_info=""),
        "expected": {"is_valid": False, "must_contain_errors": ["ответчик"]},
    },
    {
        "id": 16, "task": "validation",
        "comment": "Нет фактических обстоятельств",
        "state": _modify(_FULL_LAWSUIT, facts=""),
        "expected": {"is_valid": False, "must_contain_errors": ["обстоятельств"]},
    },
    {
        "id": 17, "task": "validation",
        "comment": "Нет требований",
        "state": _modify(_FULL_LAWSUIT, claims=""),
        "expected": {"is_valid": False, "must_contain_errors": ["требовани"]},
    },
    {
        "id": 18, "task": "validation",
        "comment": "Имущественный спор без principal_amount",
        "state": _modify(_FULL_LAWSUIT, principal_amount=0, is_property_dispute=True),
        "expected": {"is_valid": False, "must_contain_errors": ["сумма основного требования"]},
    },
    {
        "id": 19, "task": "validation",
        "comment": "Отрицательная сумма",
        "state": _modify(_FULL_LAWSUIT, principal_amount=-100),
        "expected": {"is_valid": False, "must_contain_errors": ["отрицательная сумма"]},
    },
    {
        "id": 20, "task": "validation",
        "comment": "Даты неустойки не по порядку",
        "state": _modify(_FULL_LAWSUIT, penalty_start_date="10.05.2026", penalty_end_date="01.05.2026"),
        "expected": {"is_valid": False, "must_contain_errors": ["дата"]},
    },
    {
        "id": 21, "task": "validation",
        "comment": "Претензия — недопустимая сфера",
        "state": _modify(
            _FULL_LAWSUIT,
            document_type="complaint",
            complaint_sphere="invalid_sphere",
        ),
        "expected": {"is_valid": False, "must_contain_errors": ["сфер"]},
    },
]


DATASET = CALC_CASES + VALIDATION_CASES


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
