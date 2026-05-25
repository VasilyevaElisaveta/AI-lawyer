"""
Прогон memory.summarize_messages на диалоговых историях.
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

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from memory.summarizer import summarize_messages


COLUMNS = [
    "id",
    "comment",
    "n_messages",
    "input_chars",
    "previous_summary",
    "summary",
    "summary_chars",
    "expected_keywords",
    "keywords_hit",
    "keywords_total",
    "has_all_sections",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "error",
]


_REQUIRED_SECTIONS = ("ФАКТЫ", "РЕШЕНИЯ", "ДОГОВОРЁННОСТИ", "ПАРАМЕТРЫ", "КОНТЕКСТ")


def _to_messages(items: list[dict]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for it in items:
        content = it.get("content", "")
        if it.get("role") == "ai":
            out.append(AIMessage(content=content))
        else:
            out.append(HumanMessage(content=content))
    return out


def _count_keywords(summary: str, keywords: list[str]) -> tuple[int, int]:
    if not keywords:
        return 0, 0
    summary_lower = summary.lower()
    hit = sum(1 for k in keywords if str(k).lower() in summary_lower)
    return hit, len(keywords)


def _has_all_sections(summary: str) -> bool:
    return all(section in summary for section in _REQUIRED_SECTIONS)


async def _run_one(llm, item: dict) -> dict:
    messages = _to_messages(item.get("messages") or [])
    previous = item.get("previous_summary")
    expected = item.get("expected") or {}
    keywords = expected.get("must_contain_keywords", [])
    input_chars = sum(len(getattr(m, "content", "") or "") for m in messages)
    t0 = time.perf_counter()
    summary = ""
    error = ""
    with usage_capture(llm) as (tracked_llm, usage):
        try:
            summary, _ = await summarize_messages(
                state={"usage_metadata": {}},
                messages=messages,
                llm=tracked_llm,
                previous_summary=previous,
                config=None,
            )
        except Exception as e:
            error = repr(e)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    hit, total = _count_keywords(summary, keywords)
    return {
        "id": item["id"],
        "comment": item.get("comment", ""),
        "n_messages": len(messages),
        "input_chars": input_chars,
        "previous_summary": (previous or "")[:200],
        "summary": summary,
        "summary_chars": len(summary),
        "expected_keywords": keywords,
        "keywords_hit": hit,
        "keywords_total": total,
        "has_all_sections": _has_all_sections(summary),
        "latency_ms": latency_ms,
        **usage,
        "error": error,
    }


async def _run_all(dataset: list[dict]) -> list[dict]:
    llm = build_llm(max_tokens=2048)
    rows: list[dict] = []
    for i, item in enumerate(dataset, 1):
        row = await _run_one(llm, item)
        rows.append(row)
        print(
            f"[{i}/{len(dataset)}] id={row['id']} kw={row['keywords_hit']}/{row['keywords_total']} "
            f"all_sections={row['has_all_sections']} chars={row['summary_chars']} "
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
