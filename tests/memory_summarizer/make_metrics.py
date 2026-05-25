"""
Метрики memory_summarizer:
  • keyword recall (micro / macro);
  • compression ratio (summary_chars / input_chars);
  • structural compliance (доля сводок с обязательными секциями);
  • статистика по токенам и latency.
"""
import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import read_results_csv, write_json  # noqa: E402


def _to_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def main(results_path: str, metrics_path: str) -> None:
    df = read_results_csv(results_path)
    for col in ("keywords_hit", "keywords_total", "summary_chars", "input_chars",
                "total_tokens", "latency_ms"):
        df[col] = df[col].astype(int)
    df["has_all_sections_bool"] = df["has_all_sections"].map(_to_bool)
    df["compression"] = (df["summary_chars"] / df["input_chars"]).where(df["input_chars"] > 0)

    total_hit = int(df["keywords_hit"].sum())
    total_kw = int(df["keywords_total"].sum())
    macro_recall = (
        df.loc[df["keywords_total"] > 0, "keywords_hit"]
        / df.loc[df["keywords_total"] > 0, "keywords_total"]
    ).mean()

    metrics = {
        "n": int(len(df)),
        "keyword_recall_micro": round(total_hit / total_kw, 4) if total_kw else 0.0,
        "keyword_recall_macro": round(macro_recall, 4) if not pd.isna(macro_recall) else 0.0,
        "structural_compliance": round(df["has_all_sections_bool"].mean(), 4) if len(df) else 0.0,
        "compression": df["compression"].dropna().describe().round(4).to_dict(),
        "tokens_total": int(df["total_tokens"].sum()),
        "tokens_per_case": df["total_tokens"].describe().round(2).to_dict(),
        "latency_ms": df["latency_ms"].describe().round(2).to_dict(),
        "per_case": (
            df[["id", "comment", "keywords_hit", "keywords_total",
                "summary_chars", "input_chars", "compression",
                "has_all_sections_bool", "total_tokens", "latency_ms"]]
            .rename(columns={"has_all_sections_bool": "has_all_sections"})
            .to_dict(orient="records")
        ),
    }
    write_json(metrics_path, metrics)

    print(f"n = {metrics['n']}")
    print(f"keyword recall micro = {metrics['keyword_recall_micro']}  macro = {metrics['keyword_recall_macro']}")
    print(f"structural_compliance = {metrics['structural_compliance']}")
    print(f"compression: mean={metrics['compression'].get('mean')}  min={metrics['compression'].get('min')}  max={metrics['compression'].get('max')}")
    print(f"avg tokens/case  = {metrics['tokens_per_case'].get('mean')}")
    print(f"avg latency/case = {metrics['latency_ms'].get('mean')} ms")
    print("\nper case:")
    print(
        df[["id", "keywords_hit", "keywords_total", "summary_chars",
            "compression", "has_all_sections_bool", "total_tokens", "latency_ms"]]
        .rename(columns={"has_all_sections_bool": "has_all_sections"})
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
