"""
Метрики router-classification на базе pandas + sklearn:
  • classification_report (P/R/F1, accuracy);
  • confusion_matrix;
  • средний confidence для верных/неверных;
  • accuracy по difficulty;
  • суммарные tokens и latency.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import read_results_csv, write_json


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df["correct"] = df["expected_category"] == df["predicted_category"]

    labels = sorted(set(df["expected_category"]) | set(df["predicted_category"]))
    report = classification_report(
        df["expected_category"],
        df["predicted_category"],
        labels=labels,
        zero_division=0,
        output_dict=True,
    )
    cm = pd.DataFrame(
        confusion_matrix(df["expected_category"], df["predicted_category"], labels=labels),
        index=labels,
        columns=labels,
    )

    by_difficulty = (
        df.groupby("difficulty")["correct"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "correct", "count": "total"})
    )
    by_difficulty["accuracy"] = (by_difficulty["correct"] / by_difficulty["total"]).round(4)

    confidence_stats = (
        df.groupby("correct")["confidence"]
        .agg(["count", "mean", "min", "max"])
        .round(4)
    )

    metrics = {
        "n": int(len(df)),
        "accuracy": round(report["accuracy"], 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "weighted_f1": round(report["weighted avg"]["f1-score"], 4),
        "per_class": {
            label: {k: round(v, 4) for k, v in stats.items()}
            for label, stats in report.items()
            if label in labels
        },
        "confusion_matrix": cm.to_dict(),
        "by_difficulty": by_difficulty.reset_index().to_dict(orient="records"),
        "confidence_by_correct": confidence_stats.reset_index().to_dict(orient="records"),
        "tokens_total": int(df["total_tokens"].astype(int).sum()),
        "latency_ms": df["latency_ms"].astype(int).describe().round(2).to_dict(),
    }
    write_json(metrics_path, metrics)

    print(f"n = {metrics['n']}")
    print(f"accuracy    = {metrics['accuracy']}")
    print(f"macro_f1    = {metrics['macro_f1']}")
    print(f"weighted_f1 = {metrics['weighted_f1']}")
    print("\nper-class:")
    per_class = pd.DataFrame(metrics["per_class"]).T[["precision", "recall", "f1-score", "support"]]
    print(per_class.to_string())
    print("\nconfusion matrix (rows=true, cols=pred):")
    print(cm.to_string())
    print(f"\ntokens_total = {metrics['tokens_total']}")
    print(f"saved → {metrics_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(here / "results.csv"))
    parser.add_argument("--metrics", default=str(here / "metrics.json"))
    args = parser.parse_args()
    main(args.results, args.metrics)
