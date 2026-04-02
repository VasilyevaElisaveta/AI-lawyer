from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .fields import STOP_PHRASES
from .llm_client import GigaChatClient
from .qa import qa_node
from .state import AgentState
from .document import generate_document
from .extraction import (
    build_missing_fields_prompt,
    find_missing_required_fields,
    merge_fields,
    safe_parse_json,
)
from .prompts import CLASSIFICATION_PROMPT, CLASSIFICATION_SYSTEM

@dataclass
class AgentResponse:
    reply: str
    state: AgentState
    exit_requested: bool = False
    missing_fields: list[str] = field(default_factory=list)
    qa_passed: bool = False
    generated_document: str = ""


class ContractAgent:
    def __init__(self, llm: GigaChatClient | None = None) -> None:
        self.llm = llm or GigaChatClient()

    async def process_user_message(self, user_message: str, state: AgentState | None = None) -> AgentResponse:
        state = state.copy() if state is not None else AgentState()
        user_message = user_message.strip()

        if self._is_exit_requested(user_message):
            return AgentResponse(
                reply="Хорошо, прекращаем обсуждение текущего запроса.",
                state=state,
                exit_requested=True,
            )

        state.set("last_user_message", user_message)

        await self._classify_and_extract(user_message, state)

        missing_fields = find_missing_required_fields(state)
        if missing_fields:
            state.set("awaiting_fields", missing_fields)
            return AgentResponse(
                reply=build_missing_fields_prompt(missing_fields),
                state=state,
                missing_fields=missing_fields,
            )

        state.set("awaiting_fields", [])
        document = generate_document(state)
        state.set("generated_document", document)

        qa_result = await qa_node(state, self.llm)
        if qa_result["qa_passed"]:
            return AgentResponse(
                reply=document,
                state=state,
                qa_passed=True,
                generated_document=document,
            )

        feedback = qa_result.get("qa_feedback", "Документ сгенерирован, но рецензент нашёл замечания.")
        return AgentResponse(
            reply=(
                "Документ сгенерирован, но он не проходит рецензию. \n"
                "Пожалуйста, уточните недостающие данные или измените формулировки.\n\n"
                f"{feedback}"
            ),
            state=state,
            qa_passed=False,
            generated_document=document,
        )

    def _is_exit_requested(self, text: str) -> bool:
        normalized = text.lower()
        return any(phrase in normalized for phrase in STOP_PHRASES)

    async def _classify_and_extract(self, user_message: str, state: AgentState) -> None:
        existing_state = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        prompt = CLASSIFICATION_PROMPT.format(
            existing_state=existing_state,
            user_message=user_message,
        )

        try:
            content = await self.llm.invoke([
                SystemMessage(content=CLASSIFICATION_SYSTEM),
                HumanMessage(content=prompt),
            ])
            parsed = safe_parse_json(content)
        except Exception:
            parsed = {}

        doc_type = parsed.get("doc_type") or state.get("doc_type") or "lawsuit"
        state.set("doc_type", doc_type)

        fields = parsed.get("fields", {}) or {}
        merge_fields(state, fields)

