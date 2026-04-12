import re
from typing import Any, Literal

from .documents_templates import CONTRACT_TEMPLATES

from ....utils import _normalize_space


def _has_placeholder_tokens(markdown: str) -> bool:
    patterns = [
        r"\{\{.*?\}\}",
        r"\[\s*вставить[^\]]*\]",
        r"\[\s*заполнить[^\]]*\]",
        r"\bTODO\b",
        r"\bTBD\b",
    ]
    return any(re.search(p, markdown, flags=re.IGNORECASE | re.DOTALL) for p in patterns)


def _find_heading_block(markdown: str, label: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"(?ims)^#{1,6}\s+.*{re.escape(label)}.*$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return None

    start = match.end()
    next_heading = re.search(r"(?ims)^#{1,6}\s+.+$", markdown[start:])
    end = start + next_heading.start() if next_heading else len(markdown)
    return start, end


def contract_markdown_validation_node(state):
    contract_type = state.get("contract_type")
    markdown = _normalize_space(state.get("generated_markdown", ""))
    template = CONTRACT_TEMPLATES.get(contract_type)

    errors: list[str] = []

    if not contract_type:
        errors.append("Не задан contract_type.")
    if not template:
        errors.append(f"Нет шаблона для contract_type={contract_type!r}.")
    if not markdown:
        errors.append("Сгенерированный Markdown пуст.")
    else:
        title = template.get("document_title", "") if template else ""
        if title and title.lower() not in markdown.lower():
            errors.append("В Markdown отсутствует ожидаемый заголовок документа.")

        if _has_placeholder_tokens(markdown):
            errors.append("В Markdown остались плейсхолдеры или маркеры незаполненных мест.")

        if template:
            required_sections = [s for s in template["sections"] if s["required"]]
            section_positions = []

            for section in required_sections:
                label = section["label"]
                block = _find_heading_block(markdown, label)
                if not block:
                    errors.append(f"Не найден обязательный раздел: {label}.")
                    continue

                section_positions.append((label, block[0]))

                content = markdown[block[0]:block[1]].strip()
                if len(re.sub(r"\s+", " ", content)) < 20:
                    errors.append(f"Раздел '{label}' выглядит пустым или слишком коротким.")

            if section_positions:
                positions = [pos for _, pos in section_positions]
                if positions != sorted(positions):
                    errors.append("Обязательные разделы идут в неправильном порядке.")

            optional_sections = [s for s in template["sections"] if not s["required"]]
            collected = state.get("collected_fields", {}) or {}
            for section in optional_sections:
                field_ids = section.get("field_ids", [])
                should_exist = any(collected.get(fid) not in (None, "", [], {}) for fid in field_ids)
                if should_exist:
                    if not _find_heading_block(markdown, section["label"]):
                        errors.append(
                            f"Для заполненного необязательного поля ожидается раздел: {section['label']}."
                        )

    state["markdown_validation_errors"] = errors
    state["markdown_is_valid"] = len(errors) == 0
    state["qa_passed"] = len(errors) == 0
    state["qa_feedback"] = "\n".join(errors)
    return state


def markdown_validation_router(state) -> Literal["markdown_generation", "docx_generation"]:
    return "docx_generation" if state.get("markdown_is_valid") else "markdown_generation"