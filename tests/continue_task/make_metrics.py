"""
Метрики continue_task (бинарная классификация):
  • accuracy, P/R, F1 для класса `continue=True`;
  • confusion matrix;
  • ошибки I/II рода (FP/FN);
  • accuracy по document_type.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import read_results_csv, write_json


def _to_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    df["expected_continue"] = df["expected_continue"].map(_to_bool)
    df["predicted_continue"] = df["predicted_continue"].map(_to_bool)

    y_true = df["expected_continue"].astype(int)
    y_pred = df["predicted_continue"].astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_df = pd.DataFrame(cm, index=["stop", "continue"], columns=["stop", "continue"])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    report = classification_report(
        y_true, y_pred,
        labels=[0, 1],
        target_names=["stop", "continue"],
        zero_division=0,
        output_dict=True,
    )

    by_doc = (
        df.assign(correct=df["expected_continue"] == df["predicted_continue"])
          .groupby("document_type")["correct"]
          .agg(["sum", "count"])
          .rename(columns={"sum": "correct", "count": "total"})
    )
    by_doc["accuracy"] = (by_doc["correct"] / by_doc["total"]).round(4)

    metrics = {
        "n": int(len(df)),
        "accuracy": round(report["accuracy"], 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "type_i_error": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "type_ii_error": round(fn / (fn + tp), 4) if (fn + tp) else 0.0,
        "per_class": {
            label: {k: round(v, 4) for k, v in report[label].items()}
            for label in ("stop", "continue")
        },
        "confusion_matrix": cm_df.to_dict(),
        "by_document_type": by_doc.reset_index().to_dict(orient="records"),
        "tokens_total": int(df["total_tokens"].astype(int).sum()),
        "latency_ms": df["latency_ms"].astype(int).describe().round(2).to_dict(),
    }
    write_json(metrics_path, metrics)

    print(f"n = {metrics['n']}")
    print(f"accuracy = {metrics['accuracy']}  macro_f1 = {metrics['macro_f1']}")
    print(f"TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    print(f"type_i (FP) = {metrics['type_i_error']}   type_ii (FN) = {metrics['type_ii_error']}")
    print("\nconfusion matrix (rows=true, cols=pred):")
    print(cm_df.to_string())
    print(f"\ntokens_total = {metrics['tokens_total']}")
    print(f"saved → {metrics_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(here / "results.csv"))
    parser.add_argument("--metrics", default=str(here / "metrics.json"))
    args = parser.parse_args()
    main(args.results, args.metrics)
