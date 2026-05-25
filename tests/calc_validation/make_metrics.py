"""
Метрики calc/validation (без LLM):
  • calc — accuracy по state_duty (rel.tol = 0.005), средняя/макс. относительная ошибка;
  • validation — accuracy по is_valid + покрытие обязательных подстрок ошибок,
    confusion matrix, P/R/F1 для класса invalid.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import parse_json_column, read_results_csv, write_json


CALC_REL_TOL = 0.005


def _calc_match(expected, predicted) -> tuple[bool, float]:
    try:
        e, p = float(expected), float(predicted)
    except (TypeError, ValueError):
        return False, float("inf")
    if e == 0:
        return p == 0, 0.0 if p == 0 else float("inf")
    return abs(e - p) / abs(e) <= CALC_REL_TOL, abs(e - p) / abs(e)


def _keywords_missing(expected: list[str], errors: list[str]) -> list[str]:
    joined = "\n".join(errors).lower()
    return [s for s in (expected or []) if s.lower() not in joined]


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    df["expected"] = parse_json_column(df["expected"], default={})
    df["predicted"] = parse_json_column(df["predicted"], default={})

    # ── calc ─────────────────────────────────────────────────────
    calc_df = df[df["task"] == "calc"].copy()
    calc_records = []
    for _, r in calc_df.iterrows():
        ok, rel = _calc_match(r["expected"].get("state_duty"), r["predicted"].get("state_duty"))
        calc_records.append({
            "id": r["id"],
            "comment": r["comment"],
            "expected_duty": r["expected"].get("state_duty"),
            "predicted_duty": r["predicted"].get("state_duty"),
            "match": ok,
            "rel_error": None if rel == float("inf") else round(rel, 6),
        })
    calc_table = pd.DataFrame(calc_records)
    rel_errors = calc_table["rel_error"].dropna()
    calc_summary = {
        "n": int(len(calc_table)),
        "accuracy": round(calc_table["match"].mean(), 4) if len(calc_table) else 0.0,
        "correct": int(calc_table["match"].sum()),
        "wrong": int((~calc_table["match"]).sum()),
        "avg_relative_error": round(rel_errors.mean(), 6) if len(rel_errors) else 0.0,
        "max_relative_error": round(rel_errors.max(), 6) if len(rel_errors) else 0.0,
    }

    # ── validation ───────────────────────────────────────────────
    val_df = df[df["task"] == "validation"].copy()
    val_records = []
    for _, r in val_df.iterrows():
        exp_valid = bool(r["expected"].get("is_valid"))
        pred_valid = bool(r["predicted"].get("is_valid"))
        missing = _keywords_missing(
            r["expected"].get("must_contain_errors", []),
            r["predicted"].get("validation_errors", []),
        )
        val_records.append({
            "id": r["id"],
            "comment": r["comment"],
            "expected_valid": exp_valid,
            "predicted_valid": pred_valid,
            "valid_match": exp_valid == pred_valid,
            "missing_keywords": missing,
            "joint_match": (exp_valid == pred_valid) and not missing,
        })
    val_table = pd.DataFrame(val_records)

    y_true_v = val_table["expected_valid"].astype(int) if len(val_table) else pd.Series([], dtype=int)
    y_pred_v = val_table["predicted_valid"].astype(int) if len(val_table) else pd.Series([], dtype=int)
    cm = confusion_matrix(y_true_v, y_pred_v, labels=[0, 1]) if len(val_table) else [[0, 0], [0, 0]]
    cm_df = pd.DataFrame(cm, index=["invalid", "valid"], columns=["invalid", "valid"])

    val_report = classification_report(
        y_true_v, y_pred_v,
        labels=[0, 1],
        target_names=["invalid", "valid"],
        zero_division=0,
        output_dict=True,
    ) if len(val_table) else {}

    val_summary = {
        "n": int(len(val_table)),
        "is_valid_accuracy": round(val_table["valid_match"].mean(), 4) if len(val_table) else 0.0,
        "joint_accuracy": round(val_table["joint_match"].mean(), 4) if len(val_table) else 0.0,
        "confusion_matrix": cm_df.to_dict(),
        "per_class": {
            label: {k: round(v, 4) for k, v in val_report.get(label, {}).items()}
            for label in ("invalid", "valid")
        },
        "keyword_misses": [
            {"id": r["id"], "comment": r["comment"], "missing": r["missing_keywords"]}
            for _, r in val_table.iterrows() if r["missing_keywords"]
        ],
    }

    metrics = {
        "calc": calc_summary,
        "calc_detail": calc_records,
        "validation": val_summary,
        "validation_detail": val_records,
        "latency_ms": df["latency_ms"].astype(int).describe().round(2).to_dict(),
    }
    write_json(metrics_path, metrics)

    print("calc:")
    print(f"  accuracy = {calc_summary['accuracy']}  ({calc_summary['correct']}/{calc_summary['n']})")
    print(f"  avg_rel_error = {calc_summary['avg_relative_error']}  max_rel_error = {calc_summary['max_relative_error']}")
    print()
    if not calc_table.empty:
        print(calc_table[["id", "expected_duty", "predicted_duty", "match", "rel_error", "comment"]].to_string(index=False))

    print("\nvalidation:")
    print(f"  is_valid_accuracy = {val_summary['is_valid_accuracy']}  joint_accuracy = {val_summary['joint_accuracy']}")
    print("  confusion matrix (rows=true, cols=pred):")
    print(cm_df.to_string())
    if val_summary["keyword_misses"]:
        print("  missing keywords:")
        for m in val_summary["keyword_misses"]:
            print(f"    [{m['id']}] {m['comment']} → {m['missing']}")
    print(f"\nsaved → {metrics_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(here / "results.csv"))
    parser.add_argument("--metrics", default=str(here / "metrics.json"))
    args = parser.parse_args()
    main(args.results, args.metrics)
