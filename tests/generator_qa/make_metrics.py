"""
Метрики generator + qa:
  • qa_pass_rate;
  • checklist coverage (micro и macro);
  • средние длина документа, токены и latency.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import read_results_csv, write_json


def _to_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    df["qa_passed_bool"] = df["qa_passed"].map(_to_bool)
    df["checks_hit"] = df["checks_hit"].astype(int)
    df["checks_total"] = df["checks_total"].astype(int)
    df["document_length"] = df["document_length"].astype(int)
    df["total_tokens"] = df["total_tokens"].astype(int)
    df["latency_ms"] = df["latency_ms"].astype(int)

    qa_known_mask = df["qa_passed"] != ""
    qa_known = int(qa_known_mask.sum())
    qa_passed = int(df.loc[qa_known_mask, "qa_passed_bool"].sum())

    total_hits = int(df["checks_hit"].sum())
    total_checks = int(df["checks_total"].sum())
    macro_coverage = (
        df.loc[df["checks_total"] > 0, "checks_hit"]
        / df.loc[df["checks_total"] > 0, "checks_total"]
    ).mean()

    per_case = (
        df[["id", "comment", "document_type", "qa_passed_bool",
            "checks_hit", "checks_total", "document_length",
            "total_tokens", "latency_ms", "error"]]
        .rename(columns={"qa_passed_bool": "qa_passed"})
        .to_dict(orient="records")
    )

    metrics = {
        "n": int(len(df)),
        "qa_pass_rate": round(qa_passed / qa_known, 4) if qa_known else 0.0,
        "qa_passed": qa_passed,
        "qa_known": qa_known,
        "checklist_micro": round(total_hits / total_checks, 4) if total_checks else 0.0,
        "checklist_macro": round(macro_coverage, 4) if not pd.isna(macro_coverage) else 0.0,
        "doc_length": df["document_length"].describe().round(2).to_dict(),
        "tokens_total": int(df["total_tokens"].sum()),
        "tokens_per_case": df["total_tokens"].describe().round(2).to_dict(),
        "latency_ms": df["latency_ms"].describe().round(2).to_dict(),
        "per_case": per_case,
    }
    write_json(metrics_path, metrics)

    print(f"n = {metrics['n']}")
    print(f"qa_pass_rate     = {metrics['qa_pass_rate']} ({qa_passed}/{qa_known})")
    print(f"checklist micro  = {metrics['checklist_micro']}  macro = {metrics['checklist_macro']}")
    print(f"avg doc length   = {metrics['doc_length'].get('mean')}")
    print(f"avg tokens/case  = {metrics['tokens_per_case'].get('mean')}")
    print(f"avg latency/case = {metrics['latency_ms'].get('mean')} ms")
    print("\nper case:")
    print(
        df[["id", "qa_passed_bool", "checks_hit", "checks_total",
            "document_length", "total_tokens", "latency_ms"]]
        .rename(columns={"qa_passed_bool": "qa_passed"})
        .to_string(index=False)
    )
    print(f"\nsaved → {metrics_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(here / "results.csv"))
    parser.add_argument("--metrics", default=str(here / "metrics.json"))
    args = parser.parse_args()
    main(args.results, args.metrics)
