"""Чтение/запись датасетов и результатов тестов (pandas + json)."""
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


def write_jsonl(path: str | Path, items: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)
    items: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def write_results_csv(
    path: str | Path,
    rows: list[dict],
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Сохраняет таблицу результатов теста.
    Колонки-структуры (dict/list) сериализуются в JSON-строку,
    bool — в 1/0, чтобы CSV читался обратно без сюрпризов.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if columns is not None:
        df = df.reindex(columns=columns)
    df = df.map(_serialize_cell)
    df.to_csv(path, index=False, encoding="utf-8")
    return df


def read_results_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8", keep_default_na=False)


def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)


def parse_json_column(series: pd.Series, default: Any) -> pd.Series:
    """Парсит JSON-строки в колонке. На пустых ячейках/ошибках — `default`."""
    def _parse(value: Any) -> Any:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        text = str(value).strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return default
    return series.map(_parse)


def _serialize_cell(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)
