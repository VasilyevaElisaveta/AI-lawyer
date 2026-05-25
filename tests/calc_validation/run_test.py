"""
Прогон calculator_node и validation_node на табличных кейсах (без LLM).
"""
import argparse
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.prelude import read_jsonl, write_results_csv

from agents.claims_agent.nodes.document_generation.calc import calculator_node
from agents.claims_agent.nodes.validation.validation import validation_node


COLUMNS = ["id", "task", "comment", "expected", "predicted", "latency_ms", "error"]


def _run_calc(state: dict) -> tuple[dict, str]:
    try:
        result = calculator_node(state)
        return {
            "state_duty": result.get("state_duty"),
            "total_claim": result.get("total_claim"),
        }, ""
    except Exception as e:
        return {}, repr(e)


def _run_validation(state: dict) -> tuple[dict, str]:
    try:
        result = validation_node(state)
        return {
            "is_valid": bool(result.get("is_valid")),
            "validation_errors": list(result.get("validation_errors") or []),
        }, ""
    except Exception as e:
        return {}, repr(e)


def _run_one(item: dict) -> dict:
    task = item["task"]
    state = dict(item.get("state") or {})
    t0 = time.perf_counter()
    if task == "calc":
        predicted, error = _run_calc(state)
    else:
        predicted, error = _run_validation(state)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "id": item["id"],
        "task": task,
        "comment": item.get("comment", ""),
        "expected": item.get("expected", {}),
        "predicted": predicted,
        "latency_ms": latency_ms,
        "error": error,
    }


def main(dataset_path: str, results_path: str) -> None:
    dataset = read_jsonl(dataset_path)
    rows = []
    for i, item in enumerate(dataset, 1):
        row = _run_one(item)
        rows.append(row)
        print(f"[{i}/{len(dataset)}] id={row['id']} task={row['task']} t={row['latency_ms']}ms")
    write_results_csv(results_path, rows, COLUMNS)
    print(f"Saved {len(rows)} rows → {results_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(here / "dataset.jsonl"))
    parser.add_argument("--results", default=str(here / "results.csv"))
    args = parser.parse_args()
    main(args.dataset, args.results)
