"""
Проверка намерения пользователя продолжить текущую задачу (общий модуль для агентов).
"""
import os
from typing import Any

from logger import LoggerFactory

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..utils import safe_parse_json, update_tokens_metadata


logger = LoggerFactory.get_logger(
    name="ContinueTaskCheck",
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)

CONTINUE_TASK_SYSTEM = """\
Ты определяешь, продолжает ли пользователь ту же сессию подготовки юридического документа \
или начинает другую задачу.

Контекст: ассистент уже ведёт подготовку одного конкретного документа и, возможно, \
запросил у пользователя недостающие сведения. Пришло новое сообщение — нужно решить, \
относится ли оно к этой же работе.

Принципы рассуждения:
1. continue=true — пользователь дополняет, уточняет или исправляет данные по тому же документу: \
стороны, факты, требования, суммы, адреса, сроки, приложения. Формат может быть свободным \
(списком, одной фразой, ответом на перечисленные пункты).
2. continue=false — пользователь переключился:
   • просит другой тип документа (исковое заявление и досудебная претензия — разные задачи; \
     смена с претензии на иск или наоборот всегда новая задача);
   • даёт новую команду «создай / подготовь / напиши …» на другой документ, не заполняя \
     ранее запрошенные поля;
   • задаёт общий юридический вопрос, просит другую услугу, отменяет текущую работу;
   • тема сообщения не связана с недостающими полями текущего документа.
3. Не путай «оба сообщения про право» с «одна и та же задача». Сравнивай тип документа \
   и намерение, а не общие слова.
4. Если в сессии указан тип документа A, а пользователь просит создать документ B — это \
   continue=false, даже при том же thread_id.

Верни только валидный JSON."""

CONTINUE_TASK_PROMPT = """\
{session_context}

Уже собрано по текущему документу:
{collected_fields}

Новое сообщение пользователя:
{raw_input}

Верни JSON:
{{
  "continue": true или false,
  "reasoning": "краткое объяснение на русском"
}}"""


async def check_continue_task(
    raw_input: str,
    task_label: str,
    collected_fields: dict[str, Any],
    llm,
    config: RunnableConfig | None = None,
    session_context: str = "",
    usage_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del task_label
    collected_str = "\n".join(
        f"- {key}: {value}" for key, value in collected_fields.items() if value
    ) or "(пока ничего не собрано)"

    if not session_context.strip():
        session_context = "Контекст сессии не передан."

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CONTINUE_TASK_SYSTEM),
            ("human", CONTINUE_TASK_PROMPT),
        ]
    )
    chain = prompt | llm

    try:
        response = await chain.ainvoke(
            {
                "session_context": session_context,
                "collected_fields": collected_str,
                "raw_input": raw_input,
            },
            config=config,
        )
        parsed = safe_parse_json(response.content)
        wants_continue = bool(parsed.get("continue", False))
        reasoning = str(parsed.get("reasoning", "") or "")
        logger.info(
            "continue_task: continue=%s | %s",
            wants_continue,
            reasoning[:200],
        )
        new_usage = getattr(response, "usage_metadata", {}) or {}
        if usage_metadata is not None:
            new_usage = update_tokens_metadata(
                usage_metadata,
                new_usage,
                ["input_tokens", "output_tokens", "total_tokens"],
            )
        return {
            "continue_current_task": wants_continue,
            "continue_reasoning": reasoning,
            "usage_metadata": new_usage,
        }
    except Exception as e:
        logger.error("Continue task check failed: %s", e)
        return {
            "continue_current_task": False,
            "continue_reasoning": f"ошибка проверки: {e}",
        }
