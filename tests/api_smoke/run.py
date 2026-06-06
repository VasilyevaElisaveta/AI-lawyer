import sys
from datetime import datetime, timezone
from pathlib import Path

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (TypeError, ValueError):
        pass

import httpx

from config import BASE_URL, ENV_FILE, HTTP_TIMEOUT, LOG_FILE, api_url
from smoke_tests import TestResult, run_all


class SmokeLogger:
    def __init__(self, log_file: Path) -> None:
        self._log_file = log_file
        log_file.write_text("", encoding="utf-8")

    def log(self, text: str = "") -> None:
        print(text, flush=True)
        with self._log_file.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def main() -> int:
    logger = SmokeLogger(LOG_FILE)
    started = datetime.now(timezone.utc).isoformat()

    logger.log(f"=== API smoke tests started {started} ===")
    logger.log(f"BASE_URL={BASE_URL}")
    logger.log(f"ENV_FILE={ENV_FILE} (exists={ENV_FILE.exists()})")
    logger.log(f"HTTP_TIMEOUT={HTTP_TIMEOUT}s")
    logger.log("")

    if not ENV_FILE.exists():
        logger.log("ERROR: нет tests/.env — скопируйте tests/.env.example и настройте переменные.")
        return 1

    results: list[TestResult] = []
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            health = client.get(api_url("/health"))
            if health.status_code >= 400:
                logger.log(f"ERROR: health check HTTP {health.status_code}")
                return 1
            logger.log(f"Health OK: {health.json().get('status')}")
            logger.log("")

            results = run_all(client, logger.log)
    except httpx.ConnectError as exc:
        logger.log(f"ERROR: не удалось подключиться к {BASE_URL}: {exc}")
        return 1
    except Exception as exc:
        logger.log(f"ERROR: {type(exc).__name__}: {exc}")
        return 1

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed

    logger.log(f"=== Итого: {passed}/{len(results)} passed, {failed} failed ===")
    logger.log(f"Лог: {LOG_FILE}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
