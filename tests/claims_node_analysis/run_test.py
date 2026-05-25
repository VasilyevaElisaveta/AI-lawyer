"""
Прогон classification_node (claims_agent) на датасете.
Узел не возвращает usage_metadata → токены считаем через usage_capture().
"""
import argparse
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import (
    build_llm,
    read_jsonl,
    usage_capture,
    write_results_csv,
)

from agents.claims_agent.nodes.classification.classification import (
    classification_node,
)


COLUMNS = [
    "id",
    "comment",
    "expected",
    "predicted",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "error",
]


def _extract(state: dict) -> dict:
    classification = state.get("classification_data") or {}
    return {
        "case_type": state.get("case_type") or classification.get("case_type"),
        "case_category": state.get("case_category") or classification.get("case_category"),
        "claim_nature": classification.get("claim_nature"),
        "court_jurisdiction": classification.get("court_jurisdiction"),
        "proceeding_type": classification.get("proceeding_type"),
        "plaintiff_type": classification.get("plaintiff_type"),
        "defendant_type": classification.get("defendant_type"),
        "pretrial_required": classification.get("pretrial_required"),
    }


def _run_one(llm, item: dict) -> dict:
    state = dict(item.get("state") or {})
    t0 = time.perf_counter()
    error = ""
    predicted: dict = {}
    with usage_capture(llm) as (tracked_llm, usage):
        try:
            updates = classification_node(state, tracked_llm, config=None) or {}
            merged_state = {**state, **updates}
            predicted = _extract(merged_state)
        except Exception as e:
            error = repr(e)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "id": item["id"],
        "comment": item.get("comment", ""),
        "expected": item.get("expected", {}),
        "predicted": predicted,
        "latency_ms": latency_ms,
        **usage,
        "error": error,
    }


async def _run_all(dataset: list[dict]) -> list[dict]:
    llm = build_llm(max_tokens=2048)
    rows: list[dict] = []
    for i, item in enumerate(dataset, 1):
        row = await asyncio.to_thread(_run_one, llm, item)
        rows.append(row)
        marker = "ok" if row["predicted"].get("case_type") == row["expected"].get("case_type") else "?"
        print(
            f"[{i}/{len(dataset)}] id={row['id']} {marker} "
            f"case_type={row['predicted'].get('case_type')} "
            f"nature={row['predicted'].get('claim_nature')} "
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
