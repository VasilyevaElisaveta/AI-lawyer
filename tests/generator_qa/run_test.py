"""
Прогон generator_node → qa_node на готовых состояниях.
Токены собираются единым usage_capture() (включая qa, который сам usage не возвращает).
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

from agents.claims_agent.nodes.document_generation.generator import generator_node
from agents.claims_agent.nodes.document_generation.qa import qa_node


COLUMNS = [
    "id",
    "comment",
    "document_type",
    "document_length",
    "document_snippet",
    "document_text",
    "qa_passed",
    "qa_feedback",
    "expected_checks",
    "checks_hit",
    "checks_total",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "error",
]


def _count_checks(document: str, checks: list[str]) -> tuple[int, int]:
    if not checks:
        return 0, 0
    doc_lower = document.lower()
    hit = sum(1 for c in checks if str(c).lower() in doc_lower)
    return hit, len(checks)


def _run_one(llm, item: dict) -> dict:
    state = dict(item.get("state") or {})
    expected = item.get("expected") or {}
    checks = expected.get("checks", [])
    t0 = time.perf_counter()
    document = ""
    qa_passed: bool | None = None
    qa_feedback = ""
    error = ""
    with usage_capture(llm) as (tracked_llm, usage):
        try:
            gen_updates = generator_node(state, tracked_llm, config=None) or {}
            if gen_updates.get("error"):
                error = gen_updates["error"]
            document = gen_updates.get("generated_document", "")
            state_with_doc = {**state, **gen_updates, "generated_document": document}
            qa_updates = qa_node(state_with_doc, tracked_llm, config=None) or {}
            qa_passed = bool(qa_updates.get("qa_passed"))
            qa_feedback = qa_updates.get("qa_feedback", "")
        except Exception as e:
            error = repr(e)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    hit, total = _count_checks(document, checks)
    return {
        "id": item["id"],
        "comment": item.get("comment", ""),
        "document_type": state.get("document_type", ""),
        "document_length": len(document),
        "document_snippet": document[:300].replace("\n", " "),
        "document_text": document,
        "qa_passed": qa_passed,
        "qa_feedback": (qa_feedback or "")[:500],
        "expected_checks": checks,
        "checks_hit": hit,
        "checks_total": total,
        "latency_ms": latency_ms,
        **usage,
        "error": error,
    }


async def _run_all(dataset: list[dict]) -> list[dict]:
    llm = build_llm(max_tokens=4096)
    rows: list[dict] = []
    for i, item in enumerate(dataset, 1):
        row = await asyncio.to_thread(_run_one, llm, item)
        rows.append(row)
        print(
            f"[{i}/{len(dataset)}] id={row['id']} qa_passed={row['qa_passed']} "
            f"checks={row['checks_hit']}/{row['checks_total']} "
            f"len={row['document_length']} tokens={row['total_tokens']} t={row['latency_ms']}ms"
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
