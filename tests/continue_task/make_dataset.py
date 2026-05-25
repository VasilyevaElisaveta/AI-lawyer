"""
Датасет для continue_task: 8 кейсов с активной сессией claims_agent и новым сообщением.
Поле `expected_continue` — эталон (true=продолжаем, false=новая задача).
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.common.io_utils import write_jsonl


DATASET: list[dict] = [
    {
        "id": 1,
        "comment": "Та же сессия (иск), дополнение полей",
        "session_state": {
            "document_type": "lawsuit",
            "validation_errors": [
                "Не указана информация об отправителе/истце",
                "Не указана информация об ответчике",
            ],
        },
        "raw_input": "Истец: Иванов И.И., Ответчик: ООО Ромашка",
        "expected_continue": True,
    },
    {
        "id": 2,
        "comment": "Сессия по претензии → пользователь просит иск",
        "session_state": {
            "document_type": "complaint",
            "validation_errors": ["Не указаны требования"],
        },
        "raw_input": "Создай мне иск",
        "expected_continue": False,
    },
    {
        "id": 3,
        "comment": "Сессия по иску → пользователь просит претензию",
        "session_state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Калашников В.С.",
            "validation_errors": ["Не указаны фактические обстоятельства дела"],
        },
        "raw_input": "Лучше составь претензию вместо иска",
        "expected_continue": False,
    },
    {
        "id": 4,
        "comment": "Сессия по иску → общий вопрос",
        "session_state": {
            "document_type": "lawsuit",
            "validation_errors": ["Не указаны требования"],
        },
        "raw_input": "А какой срок исковой давности по защите прав потребителей?",
        "expected_continue": False,
    },
    {
        "id": 5,
        "comment": "Сессия по претензии → прислали данные истца",
        "session_state": {
            "document_type": "complaint",
            "validation_errors": [
                "Не указана информация об отправителе",
                "Не указана информация об ответчике",
            ],
        },
        "raw_input": "Истец — Петрова Анна Сергеевна, ответчик — ИП Сидоров",
        "expected_continue": True,
    },
    {
        "id": 6,
        "comment": "Явный отказ от задачи",
        "session_state": {
            "document_type": "lawsuit",
            "validation_errors": ["Не указаны требования"],
        },
        "raw_input": "Отмени, начни заново",
        "expected_continue": False,
    },
    {
        "id": 7,
        "comment": "Уточняющий вопрос в рамках задачи",
        "session_state": {
            "document_type": "lawsuit",
            "plaintiff_info": "Иванов И.И.",
            "defendant_info": "ООО Ромашка",
            "validation_errors": ["Не указаны требования"],
        },
        "raw_input": "А я могу добавить требование о моральном вреде?",
        "expected_continue": True,
    },
    {
        "id": 8,
        "comment": "Off-topic сообщение",
        "session_state": {
            "document_type": "lawsuit",
            "validation_errors": ["Не указаны требования"],
        },
        "raw_input": "Привет, как дела?",
        "expected_continue": False,
    },
]


def main(out_path: str) -> None:
    write_jsonl(out_path, DATASET)
    print(f"Saved {len(DATASET)} examples → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "dataset.jsonl"),
    )
    args = parser.parse_args()
    main(args.out)
