"""
Прогон router classification_node на датасете.
"""
import argparse
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import build_llm, read_jsonl, usage_capture, write_results_csv

from agents.router_agent.nodes.classification import classification_node


COLUMNS = [
    "id",
    "raw_input",
    "expected_category",
    "predicted_category",
    "predicted_routed_to",
    "predicted_document_type",
    "confidence",
    "difficulty",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "error",
]


async def _run_one(llm, item: dict) -> dict:
    state = {"raw_input": item["raw_input"]}
    t0 = time.perf_counter()
    error = ""
    result: dict = {}
    with usage_capture(llm) as (tracked_llm, usage):
        try:
            result = await classification_node(state, tracked_llm, config=None) or {}
            if result.get("error"):
                error = str(result["error"])
        except Exception as e:
            error = repr(e)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "id": item["id"],
        "raw_input": item["raw_input"],
        "expected_category": item["category"],
        "predicted_category": result.get("category", ""),
        "predicted_routed_to": result.get("routed_to") or "",
        "predicted_document_type": result.get("document_type") or "",
        "confidence": result.get("classification_confidence", ""),
        "difficulty": item.get("difficulty", ""),
        "latency_ms": latency_ms,
        **usage,
        "error": error,
    }


async def _run_all(dataset: list[dict]) -> list[dict]:
    llm = build_llm(max_tokens=512)
    rows: list[dict] = []
    for i, item in enumerate(dataset, 1):
        row = await _run_one(llm, item)
        rows.append(row)
        marker = "ok" if row["predicted_category"] == row["expected_category"] else "FAIL"
        print(
            f"[{i}/{len(dataset)}] id={row['id']} {marker} "
            f"pred={row['predicted_category']} exp={row['expected_category']} "
            f"tokens={row['total_tokens']} t={row['latency_ms']}ms"
        )
    return rows


def main(dataset_path: str, results_path: str) -> None:
    dataset = read_jsonl(dataset_path)
    rows = asyncio.run(_run_all(dataset))
    write_results_csv(results_path, rows, COLUMNS)
    print(f"Saved {len(rows)} rows → {results_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(here / "dataset.jsonl"))
    parser.add_argument("--results", default=str(here / "results.csv"))
    args = parser.parse_args()
    main(args.dataset, args.results)
