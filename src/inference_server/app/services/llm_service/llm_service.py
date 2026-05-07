import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tracers.context import collect_runs

from logger import LoggerFactory

from agents.llm_client import create_gigachat

from .prompts import CHAT_NAME_PROMPT, CHAT_NAME_SYSTEM


logger = logger = LoggerFactory.get_logger(
    name=__name__,
    logs_path=os.getenv("LOGS_DIR"),
    log_file=os.getenv("LOGS_FILE") if os.getenv("MODE") != "DEBUG" else None,
)


class LLMService:
    def __init__(self, model, config, **kwargs):
        self.llm = create_gigachat(model, config=config, **kwargs)
    
    async def aget_chat_name(self, raw_input):
        input_d = {
            "raw_input": raw_input,
        }
        prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_NAME_SYSTEM),
            ("human", CHAT_NAME_PROMPT)
        ])
        chain = prompt | self.llm
        with collect_runs() as runs_cb:
            response = await chain.ainvoke(
                input_d,
                config={
                    "run_name": "GeneralQuestionAgent",
                },
            )
        root_run = runs_cb.traced_runs[-1]
        usage = response.usage_metadata or {}
        result = {
            "response": response,
            "metadata": {
                "run_id": str(root_run.id),
                "trace_id": str(root_run.trace_id),
                "latency_ms": int((root_run.end_time - root_run.start_time).total_seconds() * 1000),
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
            },
        }
        logger.debug(f"Got result: {result}")
        return result