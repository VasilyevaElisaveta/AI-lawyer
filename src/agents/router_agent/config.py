from __future__ import annotations

from typing import Literal

Category = Literal["contract", "pretrial_claim", "lawsuit", "simple_question"]

ROUTER_KEYWORDS: dict[Category, list[str]] = {
    "pretrial_claim": [
        "претензи", "требован", "претензия", "досудеб", "урегулиров", "жалоб",
    ],
    "lawsuit": [
        "иск", "суд", "судеб", "подать в суд", "заявление в суд", "ответчик", "истец",
    ],
    "contract": [
        "договор", "контракт", "соглашение", "условия", "аренда", "купли", "продажи", "оферта",
    ],
    "simple_question": [],
}
