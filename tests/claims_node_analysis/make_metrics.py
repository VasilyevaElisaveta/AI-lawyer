"""
Метрики case_analysis (мульти-полевая классификация).
По каждому из жёстких полей (case_type, claim_nature, court_jurisdiction):
  • classification_report (P/R/F1, support, accuracy);
  • confusion_matrix.
joint_accuracy — все 3 поля совпали одновременно.
category_soft_accuracy — predicted.case_category входит в expected.acceptable_categories.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import parse_json_column, read_results_csv, write_json


STRICT_FIELDS = ["case_type", "claim_nature", "court_jurisdiction"]


def _field_report(y_true: list[str], y_pred: list[str]) -> dict:
    labels = sorted(set(y_true) | set(y_pred))
    if not labels:
        return {}
    report = classification_report(
        y_true, y_pred,
        labels=labels,
        zero_division=0,
        output_dict=True,
    )
    cm = pd.DataFrame(
        confusion_matrix(y_true, y_pred, labels=labels),
        index=labels, columns=labels,
    )
    return {
        "accuracy": round(report["accuracy"], 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "weighted_f1": round(report["weighted avg"]["f1-score"], 4),
        "per_class": {
            label: {k: round(v, 4) for k, v in report[label].items()}
            for label in labels
        },
        "confusion_matrix": cm.to_dict(),
        "_cm_df": cm,
    }


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    df["expected"] = parse_json_column(df["expected"], default={})
    df["predicted"] = parse_json_column(df["predicted"], default={})

    per_field: dict[str, dict] = {}
    correctness = pd.DataFrame(index=df.index)
    for field in STRICT_FIELDS:
        y_true = df["expected"].map(lambda d, f=field: str(d.get(f) or ""))
        y_pred = df["predicted"].map(lambda d, f=field: str(d.get(f) or ""))
        per_field[field] = _field_report(y_true.tolist(), y_pred.tolist())
        correctness[field] = (y_true == y_pred)

    joint_accuracy = round(correctness.all(axis=1).mean(), 4) if len(df) else 0.0

    category_mask = df["expected"].map(lambda d: bool(d.get("acceptable_categories")))
    category_subset = df[category_mask]
    category_hits = sum(
        row["predicted"].get("case_category") in (row["expected"].get("acceptable_categories") or [])
        for _, row in category_subset.iterrows()
    )
    category_total = int(len(category_subset))

    metrics = {
        "n": int(len(df)),
        "joint_accuracy": joint_accuracy,
        "category_soft_accuracy": round(category_hits / category_total, 4) if category_total else 0.0,
        "category_hits": category_hits,
        "category_total": category_total,
        "per_field": {
            field: {k: v for k, v in report.items() if k != "_cm_df"}
            for field, report in per_field.items()
        },
        "tokens_total": int(df["total_tokens"].astype(int).sum()),
        "latency_ms": df["latency_ms"].astype(int).describe().round(2).to_dict(),
    }
    write_json(metrics_path, metrics)

    print(f"n = {metrics['n']}")
    print(f"joint_accuracy (все 3 поля)   = {metrics['joint_accuracy']}")
    print(f"category_soft_accuracy        = {metrics['category_soft_accuracy']} ({category_hits}/{category_total})")
    for field, report in per_field.items():
        print(f"\n--- {field} ---")
        print(f"accuracy={report['accuracy']}  macro_f1={report['macro_f1']}  weighted_f1={report['weighted_f1']}")
        print("confusion matrix (rows=true, cols=pred):")
        print(report["_cm_df"].to_string())
    print(f"\ntokens_total = {metrics['tokens_total']}")
    print(f"saved → {metrics_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(here / "results.csv"))
    parser.add_argument("--metrics", default=str(here / "metrics.json"))
    args = parser.parse_args()
    main(args.results, args.metrics)
