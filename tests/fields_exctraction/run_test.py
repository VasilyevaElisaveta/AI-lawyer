"""
Прогон intake_node на датасете. Сохраняет CSV с предсказанными полями.
"""
import argparse
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import build_llm, read_jsonl, usage_capture, write_results_csv  # noqa: E402

from agents.claims_agent.nodes.document_generation.intake import intake_node  # noqa: E402


EVAL_FIELDS = [
    "plaintiff_info",
    "defendant_info",
    "claims",
    "facts",
    "principal_amount",
    "penalty_amount",
    "moral_damage",
    "court_expenses",
]

COLUMNS = [
    "id",
    "raw_input",
    "document_type",
    "difficulty",
    "expected_fields",
    "predicted_fields",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "error",
]


def _run_one(llm, item: dict) -> dict:
    state = {
        "raw_input": item["raw_input"],
        "document_type": item.get("document_type", "lawsuit"),
        "document_type_locked": True,
        "usage_metadata": {},
    }
    t0 = time.perf_counter()
    predicted: dict = {}
    error = ""
    with usage_capture(llm) as (tracked_llm, usage):
        try:
            updates = intake_node(state, tracked_llm, config=None) or {}
            predicted = {k: v for k, v in updates.items() if k in EVAL_FIELDS}
        except Exception as e:
            error = repr(e)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "id": item["id"],
        "raw_input": item["raw_input"],
        "document_type": item.get("document_type", "lawsuit"),
        "difficulty": item.get("difficulty", ""),
        "expected_fields": item.get("expected_fields", {}),
        "predicted_fields": predicted,
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
        print(
            f"[{i}/{len(dataset)}] id={row['id']} "
            f"pred_keys={list(row['predicted_fields'].keys())} "
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
