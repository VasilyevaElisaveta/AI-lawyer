from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class ChatNameRequest(BaseModel):
    raw_input: str
    thread_id: str


class ChatNameResponse(BaseModel):
    thread_id: str
    chat_name: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    run_id: str
    trace_id: str
    process_name: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_input: str
    thread_id: str
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class ChatAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_input: str
    thread_id: str
    user_metadata: dict[str, Any] = Field(default_factory=dict)
    request_metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    document_comment: str = ""
    handled_by_agent: bool = True
    document_created: bool = False
    is_error: bool = False
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    run_id: str
    trace_id: str
    process_name: str