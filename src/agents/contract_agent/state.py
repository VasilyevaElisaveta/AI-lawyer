from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class ContractAgentState(TypedDict, total=False):
    current_node: str

    messages: Annotated[list, add_messages]
    messages_str: str

    conversation_summary: str
    total_tokens: int

    doc_type: str

    raw_input: str
    input_data: dict[str, Any]

    contract_type: str
    contract_fields: dict
    collected_fields: dict

    case_type: str
    case_category: str

    validation_errors: list[str]
    validation_warnings: list[str]
    is_valid: bool
    response_to_user: str | None

    applicable_laws: str
    legal_positions: str

    generated_documents: list[str]
    summarized_documents: list[str]
    summarized_documents_str: str

    qa_passed: bool
    qa_feedback: str
    qa_attempts: int

    document_template: dict[str, Any]
    generated_markdown: str
    markdown_validation_errors: list[str]
    markdown_is_valid: bool
    markdown_generation_attempts: int
    document_created: bool

    generated_docx_base64: str