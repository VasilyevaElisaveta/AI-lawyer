import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from config import api_url


GENERAL_QUESTION = "Что такое срок исковой давности?"
LAWSUIT_REQUEST = (
    "Составь иск. Истец: Иванов Иван Иванович. Ответчик: ООО Ромашка. "
    "Требования: взыскать 200 000 рублей за некачественный товар."
)
COMPLAINT_REQUEST = (
    "Составь досудебную претензию. Отправитель: Петров П.П. "
    "Получатель: ООО Ромашка. Требования: вернуть 50 000 рублей за бракованный товар."
)
CHAT_NAME_INPUT = "Как оформить льготную ипотеку для молодой семьи?"


@dataclass
class TestResult:
    name: str
    passed: bool
    http_status: int
    message: str
    duration_ms: int


def format_result(result: TestResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    return (
        f"[{status}] {result.name} | HTTP {result.http_status} | "
        f"{result.duration_ms} ms | {result.message}"
    )


def _thread_id(prefix: str) -> str:
    return f"smoke-{prefix}-{uuid.uuid4()}"


def _log_stream_event(log: Callable[[str], None], raw_line: str) -> None:
    try:
        event = json.loads(raw_line)
    except json.JSONDecodeError:
        return
    event_type = event.get("type", "?")
    if event_type == "progress":
        stage = event.get("stage", "")
        content = (event.get("content") or "").replace("\n", " ")[:120]
        log(f"    stream progress [{stage}]: {content}")
    elif event_type == "result":
        log(
            f"    stream result: process_name={event.get('process_name', '—')}, "
            f"document_created={event.get('document_created', False)}"
        )
    elif event_type == "error":
        log(f"    stream error: {event.get('message', event)}")


def _check_json_response(name: str, response: httpx.Response, t0: float) -> TestResult:
    duration_ms = int((time.perf_counter() - t0) * 1000)
    if response.status_code >= 400:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"HTTP {response.status_code}: {response.text[:500]}",
            duration_ms=duration_ms,
        )
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"Ответ не JSON: {exc}",
            duration_ms=duration_ms,
        )
    if data.get("is_error"):
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"is_error=true, reply={data.get('reply', '')[:300]}",
            duration_ms=duration_ms,
        )
    reply = (data.get("reply") or data.get("chat_name") or "").strip()
    if not reply and not data.get("document_created"):
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message="Пустой reply в успешном ответе",
            duration_ms=duration_ms,
        )
    return TestResult(
        name=name,
        passed=True,
        http_status=response.status_code,
        message=f"OK, process_name={data.get('process_name', '—')}",
        duration_ms=duration_ms,
    )


def _parse_ndjson_events(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def _check_stream_response(
    name: str,
    response: httpx.Response,
    lines: list[str],
    t0: float,
) -> TestResult:
    duration_ms = int((time.perf_counter() - t0) * 1000)
    if response.status_code >= 400:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"HTTP {response.status_code}: {response.text[:500]}",
            duration_ms=duration_ms,
        )
    try:
        events = _parse_ndjson_events(lines)
    except json.JSONDecodeError as exc:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"NDJSON parse error: {exc}",
            duration_ms=duration_ms,
        )

    for event in events:
        if event.get("type") == "error":
            return TestResult(
                name=name,
                passed=False,
                http_status=response.status_code,
                message=f"stream error: {event.get('message', event)}",
                duration_ms=duration_ms,
            )

    results = [event for event in events if event.get("type") == "result"]
    if not results:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"Нет финального result в потоке ({len(events)} событий)",
            duration_ms=duration_ms,
        )

    final = results[-1]
    if final.get("is_error"):
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"result is_error=true: {final.get('error') or final.get('reply', '')[:300]}",
            duration_ms=duration_ms,
        )
    return TestResult(
        name=name,
        passed=True,
        http_status=response.status_code,
        message=f"OK, events={len(events)}, process_name={final.get('process_name', '—')}",
        duration_ms=duration_ms,
    )


def _run_case(
    client: httpx.Client,
    log: Callable[[str], None],
    index: int,
    total: int,
    name: str,
    runner: Callable[[], TestResult],
) -> TestResult:
    log(f">>> [{index}/{total}] {name}")
    t0 = time.perf_counter()
    result = runner()
    elapsed = int((time.perf_counter() - t0) * 1000)
    if result.duration_ms == 0:
        result.duration_ms = elapsed
    log(format_result(result))
    log("")
    return result


def test_invoke_general_question(client: httpx.Client) -> TestResult:
    name = "POST /invoke — general_questions (через router)"
    t0 = time.perf_counter()
    response = client.post(
        api_url("/invoke"),
        json={"raw_input": GENERAL_QUESTION, "thread_id": _thread_id("invoke-gq")},
    )
    return _check_json_response(name, response, t0)


def test_invoke_stream_lawsuit(
    client: httpx.Client,
    log: Callable[[str], None],
) -> TestResult:
    name = "POST /invoke/stream — создание иска (через router)"
    t0 = time.perf_counter()
    lines: list[str] = []
    with client.stream(
        "POST",
        api_url("/invoke/stream"),
        json={"raw_input": LAWSUIT_REQUEST, "thread_id": _thread_id("stream-lawsuit")},
    ) as response:
        for line in response.iter_lines():
            if line is not None:
                lines.append(line)
                _log_stream_event(log, line)
    return _check_stream_response(name, response, lines, t0)


def test_invoke_agent_stream(
    client: httpx.Client,
    agent_type: str,
    raw_input: str,
    request_metadata: dict[str, Any] | None,
    log: Callable[[str], None],
    *,
    label: str | None = None,
) -> TestResult:
    suffix = f" ({label})" if label else ""
    name = f"POST /invoke/{agent_type}/stream{suffix}"
    payload: dict[str, Any] = {
        "raw_input": raw_input,
        "thread_id": _thread_id(f"stream-{agent_type}-{label or 'default'}"),
    }
    if request_metadata:
        payload["request_metadata"] = request_metadata
    t0 = time.perf_counter()
    lines: list[str] = []
    with client.stream(
        "POST",
        api_url(f"/invoke/{agent_type}/stream"),
        json=payload,
    ) as response:
        for line in response.iter_lines():
            if line is not None:
                lines.append(line)
                _log_stream_event(log, line)
    return _check_stream_response(name, response, lines, t0)


def test_invoke_agent(
    client: httpx.Client,
    agent_type: str,
    raw_input: str,
    request_metadata: dict[str, Any] | None = None,
    *,
    label: str | None = None,
) -> TestResult:
    suffix = f" ({label})" if label else ""
    name = f"POST /invoke/{agent_type}{suffix}"
    payload: dict[str, Any] = {
        "raw_input": raw_input,
        "thread_id": _thread_id(f"invoke-{agent_type}-{label or 'default'}"),
    }
    if request_metadata:
        payload["request_metadata"] = request_metadata
    t0 = time.perf_counter()
    response = client.post(api_url(f"/invoke/{agent_type}"), json=payload)
    return _check_json_response(name, response, t0)


def test_chat_name(client: httpx.Client) -> TestResult:
    name = "POST /chat_name"
    t0 = time.perf_counter()
    response = client.post(
        api_url("/chat_name"),
        json={"raw_input": CHAT_NAME_INPUT, "thread_id": _thread_id("chat-name")},
    )
    duration_ms = int((time.perf_counter() - t0) * 1000)
    if response.status_code >= 400:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"HTTP {response.status_code}: {response.text[:500]}",
            duration_ms=duration_ms,
        )
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message=f"Ответ не JSON: {exc}",
            duration_ms=duration_ms,
        )
    chat_name = (data.get("chat_name") or "").strip()
    if not chat_name:
        return TestResult(
            name=name,
            passed=False,
            http_status=response.status_code,
            message="Пустой chat_name",
            duration_ms=duration_ms,
        )
    return TestResult(
        name=name,
        passed=True,
        http_status=response.status_code,
        message=f"OK, chat_name={chat_name!r}",
        duration_ms=duration_ms,
    )


def run_all(client: httpx.Client, log: Callable[[str], None]) -> list[TestResult]:
    cases: list[tuple[str, Callable[[], TestResult]]] = [
        (
            "POST /invoke — general_questions (через router)",
            lambda: test_invoke_general_question(client),
        ),
        (
            "POST /invoke/stream — создание иска (через router)",
            lambda: test_invoke_stream_lawsuit(client, log),
        ),
        (
            "POST /invoke/general_questions_agent/stream",
            lambda: test_invoke_agent_stream(
                client, "general_questions_agent", GENERAL_QUESTION, None, log
            ),
        ),
        (
            "POST /invoke/claims_agent/stream (иск)",
            lambda: test_invoke_agent_stream(
                client,
                "claims_agent",
                LAWSUIT_REQUEST,
                {"document_type": "lawsuit"},
                log,
                label="иск",
            ),
        ),
        (
            "POST /invoke/claims_agent/stream (претензия)",
            lambda: test_invoke_agent_stream(
                client,
                "claims_agent",
                COMPLAINT_REQUEST,
                {"document_type": "complaint"},
                log,
                label="претензия",
            ),
        ),
        (
            "POST /invoke/router_agent/stream",
            lambda: test_invoke_agent_stream(
                client, "router_agent", GENERAL_QUESTION, None, log
            ),
        ),
        (
            "POST /invoke/general_questions_agent",
            lambda: test_invoke_agent(client, "general_questions_agent", GENERAL_QUESTION),
        ),
        (
            "POST /invoke/claims_agent (иск)",
            lambda: test_invoke_agent(
                client,
                "claims_agent",
                LAWSUIT_REQUEST,
                {"document_type": "lawsuit"},
                label="иск",
            ),
        ),
        (
            "POST /invoke/claims_agent (претензия)",
            lambda: test_invoke_agent(
                client,
                "claims_agent",
                COMPLAINT_REQUEST,
                {"document_type": "complaint"},
                label="претензия",
            ),
        ),
        (
            "POST /invoke/router_agent",
            lambda: test_invoke_agent(client, "router_agent", GENERAL_QUESTION),
        ),
        (
            "POST /chat_name",
            lambda: test_chat_name(client),
        ),
    ]

    total = len(cases)
    results: list[TestResult] = []
    for index, (name, runner) in enumerate(cases, start=1):
        results.append(_run_case(client, log, index, total, name, runner))
    return results
