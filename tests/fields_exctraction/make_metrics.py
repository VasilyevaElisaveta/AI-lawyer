"""
Метрики извлечения полей (intake) на базе pandas + sklearn:
  • per-field precision/recall/F1 (через sklearn по бинарной маске «совпало»);
  • micro/macro F1 по всем полям;
  • hallucination rate (поле есть в pred, отсутствует в gold);
  • full-coverage rate (все эталонные поля совпали).

Логика сопоставления:
  • для строковых полей — fuzzy (SequenceMatcher) с порогом 0.6 + подстрока;
  • для числовых — относительный допуск 2 %.
"""
import argparse
from difflib import SequenceMatcher
from pathlib import Path
import sys
from typing import Any

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import parse_json_column, read_results_csv, write_json  # noqa: E402


STRING_FIELDS = ("plaintiff_info", "defendant_info", "claims", "facts")
NUMERIC_FIELDS = ("principal_amount", "penalty_amount", "moral_damage", "court_expenses")
ALL_FIELDS = STRING_FIELDS + NUMERIC_FIELDS

FUZZY_THRESHOLD = 0.6
NUMERIC_REL_TOL = 0.02


def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (int, float)):
        return v != 0
    return True


def _string_match(gold: str, pred: str) -> tuple[bool, float]:
    g = (gold or "").strip().lower()
    p = (pred or "").strip().lower()
    if not g and not p:
        return True, 1.0
    if not g or not p:
        return False, 0.0
    if g in p or p in g:
        return True, 1.0
    score = SequenceMatcher(None, g, p).ratio()
    return score >= FUZZY_THRESHOLD, score


def _numeric_match(gold: Any, pred: Any) -> bool:
    try:
        g, p = float(gold), float(pred)
    except (TypeError, ValueError):
        return False
    if g == 0 and p == 0:
        return True
    if g == 0 or p == 0:
        return False
    return abs(g - p) / max(abs(g), abs(p)) <= NUMERIC_REL_TOL


def _field_outcome(gold: dict, pred: dict, field: str) -> tuple[int, int, int, int, float]:
    """Возвращает (y_true_pos, y_pred_pos, hallucination_flag, exact_match_flag, score)."""
    g, p = gold.get(field), pred.get(field)
    gh, ph = _has_value(g), _has_value(p)
    if gh and ph:
        if field in NUMERIC_FIELDS:
            matched, score = _numeric_match(g, p), 1.0 if _numeric_match(g, p) else 0.0
        else:
            matched, score = _string_match(str(g), str(p))
        return 1, 1 if matched else 0, 0, 1 if matched else 0, score
    if gh and not ph:
        return 1, 0, 0, 0, 0.0
    if not gh and ph:
        return 0, 1, 1, 0, 0.0
    return 0, 0, 0, 1, 1.0


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    df["expected_fields"] = parse_json_column(df["expected_fields"], default={})
    df["predicted_fields"] = parse_json_column(df["predicted_fields"], default={})

    field_records: dict[str, list[dict]] = {f: [] for f in ALL_FIELDS}
    case_full_coverage: list[bool] = []
    halluc_count = 0

    for _, row in df.iterrows():
        gold = row["expected_fields"] or {}
        pred = row["predicted_fields"] or {}
        case_correct = 0
        case_total_gold = 0
        for field in ALL_FIELDS:
            y_t, y_p, halluc, em, score = _field_outcome(gold, pred, field)
            halluc_count += halluc
            field_records[field].append({
                "y_true": y_t,
                "y_pred": y_p,
                "exact_match": em,
                "score": score,
            })
            if _has_value(gold.get(field)):
                case_total_gold += 1
                if y_p == 1:
                    case_correct += 1
        case_full_coverage.append(case_total_gold > 0 and case_correct == case_total_gold)

    per_field: dict[str, dict] = {}
    for field, records in field_records.items():
        sub = pd.DataFrame(records)
        p, r, f1, _ = precision_recall_fscore_support(
            sub["y_true"], sub["y_pred"], average="binary",
            pos_label=1, zero_division=0,
        )
        per_field[field] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "exact_match": int(sub["exact_match"].sum()),
            "avg_score": round(sub["score"].mean(), 4),
            "support_gold": int(sub["y_true"].sum()),
            "support_pred": int(sub["y_pred"].sum()),
        }

    # micro
    micro_rows = pd.concat([pd.DataFrame(r) for r in field_records.values()], ignore_index=True)
    micro_p, micro_r, micro_f1, _ = precision_recall_fscore_support(
        micro_rows["y_true"], micro_rows["y_pred"], average="binary",
        pos_label=1, zero_division=0,
    )
    macro_f1 = round(pd.Series([m["f1"] for m in per_field.values()]).mean(), 4)

    metrics = {
        "n_cases": int(len(df)),
        "macro_f1": macro_f1,
        "micro_precision": round(micro_p, 4),
        "micro_recall": round(micro_r, 4),
        "micro_f1": round(micro_f1, 4),
        "hallucinations": int(halluc_count),
        "full_coverage_rate": round(sum(case_full_coverage) / len(df), 4) if len(df) else 0.0,
        "per_field": per_field,
        "tokens_total": int(df["total_tokens"].astype(int).sum()),
        "latency_ms": df["latency_ms"].astype(int).describe().round(2).to_dict(),
    }
    write_json(metrics_path, metrics)

    print(f"n = {metrics['n_cases']}")
    print(
        f"micro: P={metrics['micro_precision']} R={metrics['micro_recall']} F1={metrics['micro_f1']}; "
        f"macro F1 = {metrics['macro_f1']}"
    )
    print(f"hallucinations = {halluc_count}; full_coverage_rate = {metrics['full_coverage_rate']}")
    print("\nper-field:")
    print(pd.DataFrame(per_field).T.to_string())
    print(f"\ntokens_total = {metrics['tokens_total']}")
    print(f"saved → {metrics_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(here / "results.csv"))
    parser.add_argument("--metrics", default=str(here / "metrics.json"))
    args = parser.parse_args()
    main(args.results, args.metrics)
