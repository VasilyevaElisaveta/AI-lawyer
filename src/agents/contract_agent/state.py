from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class ContractAgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]

    conversation_summary: str
    total_tokens: int

    doc_type: str

    raw_input: str
    input_data: dict[str, Any]

    party_a_info: str
    party_b_info: str
    contract_subject: str
    contract_terms: str
    governing_law: str
    contract_amount: float

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

    qa_passed: bool
    qa_feedback: str
    qa_attempts: int

    final_document: str

    document_template: dict[str, Any]
    generated_markdown: str
    markdown_validation_errors: list[str]
    markdown_is_valid: bool

    generated_docx_path: str
    generated_docx_name: str
    generated_docx_base64: str

    document_summary: str
    summary_source: str
    summary_attempts: int