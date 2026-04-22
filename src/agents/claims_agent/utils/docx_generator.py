"""
Генерация DOCX-документа из текста искового заявления.
"""
from __future__ import annotations

import base64
import io
import unicodedata
from typing import Any

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .logger import get_logger

logger = get_logger(__name__)


def generate_docx_base64(document_text: str, metadata: dict[str, Any] | None = None) -> str:
    """
    Генерирует DOCX-файл из текста и возвращает base64-строку.

    Args:
        document_text: Текст искового заявления
        metadata: Метаданные (истец, ответчик и т.д.)

    Returns:
        Base64-строка DOCX-файла
    """
    logger.info("Generating DOCX from text (length: %d chars)", len(document_text))

    metadata = metadata or {}

    # Создаём документ
    doc = Document()

    # Настройка полей (2 см со всех сторон)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.79)    # ~2 см
        section.bottom_margin = Inches(0.79)
        section.left_margin = Inches(1.18)   # ~3 см (для подшивки)
        section.right_margin = Inches(0.59)  # ~1.5 см

    # Парсим текст и форматируем
    _add_formatted_content(doc, document_text)

    # Добавляем метаданные как свойства документа (с ограничением 255 символов)
    if metadata:
        core_props = doc.core_properties
        core_props.title = "Исковое заявление"

        # Извлекаем короткие имена
        plaintiff_short = _extract_short_name(metadata.get('plaintiff', 'Не указан'), max_length=80)
        defendant_short = _extract_short_name(metadata.get('defendant', 'Не указан'), max_length=80)

        # Формируем subject (максимум 255 символов)
        subject = f"Истец: {plaintiff_short} / Ответчик: {defendant_short}"
        if len(subject) > 255:
            subject = subject[:252] + "..."

        core_props.subject = subject
        core_props.keywords = "исковое заявление, судебный документ"

    # Сохраняем в BytesIO
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Конвертируем в base64
    docx_bytes = buffer.read()
    docx_base64 = base64.b64encode(docx_bytes).decode('utf-8')

    logger.info("DOCX generated, size: %d bytes, base64 length: %d", len(docx_bytes), len(docx_base64))

    return docx_base64


def _extract_short_name(full_info: str, max_length: int = 80) -> str:
    """
    Извлекает короткое имя из полной информации.

    Примеры:
        "Иванов Иван Иванович, паспорт..." → "Иванов Иван Иванович"
        "ООО «Ромашка», ИНН 1234..." → "ООО «Ромашка»"
    """
    if not full_info:
        return "Не указан"

    # Берём первую строку до первой запятой или переноса
    lines = full_info.split('\n')
    first_line = lines[0].strip()

    parts = first_line.split(',')
    name = parts[0].strip() if parts else first_line

    # Обрезаем до max_length
    if len(name) > max_length:
        name = name[:max_length - 3] + "..."

    return name


def _add_formatted_content(doc: Document, text: str) -> None:
    """
    Добавляет текст в документ с форматированием.

    Правила:
    - Шапка (первые строки до заголовка) → выравнивание справа, Times New Roman 12pt
    - Заголовок "ИСКОВОЕ ЗАЯВЛЕНИЕ" → по центру, жирный, 14pt
    - Основной текст → Times New Roman 14pt, междустрочный интервал 1.5
    - Подзаголовки (начинаются с цифры + точка) → жирный
    """
    lines = text.split('\n')

    in_header = True

    for line in lines:
        line_stripped = line.strip()

        # Пропускаем пустые строки
        if not line_stripped:
            doc.add_paragraph()
            continue

        # Определение типа строки
        if "ИСКОВОЕ ЗАЯВЛЕНИЕ" in line_stripped.upper():
            # Заголовок
            p = doc.add_paragraph(line_stripped)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.font.bold = True
            in_header = False
            continue

        if in_header:
            # Шапка документа (до заголовка) — справа
            p = doc.add_paragraph(line_stripped)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            continue

        # Подзаголовки (начинаются с "1.", "2." и т.д.)
        if line_stripped and line_stripped[0].isdigit() and '.' in line_stripped[:5]:
            p = doc.add_paragraph(line_stripped)
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.font.bold = True
            p.paragraph_format.space_before = Pt(6)
            continue

        # Обычный текст
        p = doc.add_paragraph(line_stripped)
        run = p.runs[0]
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.first_line_indent = Inches(0.5)  # Абзацный отступ