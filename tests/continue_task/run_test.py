"""
Прогон `evaluate_continue_task` на датасете. Сохраняет CSV с предсказаниями.
"""
import argparse
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import build_llm, read_jsonl, usage_capture, write_results_csv

from agents.claims_agent.nodes.continue_task import evaluate_continue_task


COLUMNS = [
    "id",
    "comment",
    "raw_input",
    "document_type",
    "expected_continue",
    "predicted_continue",
    "reasoning",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "error",
]


async def _run_one(llm, item: dict) -> dict:
    raw_input = item["raw_input"]
    session_state = item.get("session_state", {})
    t0 = time.perf_counter()
    predicted = None
    reasoning = ""
    error = ""
    with usage_capture(llm) as (tracked_llm, usage):
        try:
            result = await evaluate_continue_task(raw_input, session_state, tracked_llm)
            predicted = bool(result.get("continue_current_task", False))
            reasoning = str(result.get("continue_reasoning") or "")
        except Exception as e:
            error = repr(e)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "id": item["id"],
        "comment": item.get("comment", ""),
        "raw_input": raw_input,
        "document_type": session_state.get("document_type", ""),
        "expected_continue": bool(item["expected_continue"]),
        "predicted_continue": predicted,
        "reasoning": reasoning,
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
        marker = "ok" if row["predicted_continue"] == row["expected_continue"] else "FAIL"
        print(
            f"[{i}/{len(dataset)}] id={row['id']} {marker} "
            f"pred={row['predicted_continue']} exp={row['expected_continue']} "
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
