DECISION_SYSTEM = \
"""
Ты - интеллектуальный юридический ассистент.
Твоя задача - понять из запроса пользователя - обращается ли он к каким либо документам. И в зависимости от решения вернуть определённый результат.
Возвращай только JSON.
"""

DECISION_PROMPT = \
"""
История диалога:
{messages_str}
Сводки документов:
{summarized_documents_str}
Вопрос:
{raw_input}
Задача:
Определи, нужно ли использовать полноценный текст документов, или хватает суммаризированных.
Ответь строго в JSON формате:
Вариант 1 (если нужны цельные документы):
{{
  "need_documents": true,
  "document_ids": [список индексов],
  "reason": "почему"
}}
Вариант 2 (если суммаризированных документов хватает):
{{
  "need_documents": false,
  "answer": "финальный ответ пользователю"
}}
ВАЖНО:
- Не смешивай варианты
- Не добавляй текст вне JSON
"""

ANSWER_SYSTEM = \
"""
Ты - интеллектуальный юридический ассистент.
Твоя задача - ответить на вопрос пользователя, используй предоставленный контекст.
"""

ANSWER_PROMPT = \
"""
Контекст:
{context}
Вопрос:
{raw_input}
"""


def make_decision_dict(raw_input, messages_str, summarized_documents_str):
    return {
        "raw_input": raw_input,
        "messages_str": messages_str,
        "summarized_documents_str": summarized_documents_str,
    }


def make_answer_dict(raw_input, context):
    return {
        "raw_input": raw_input,
        "context": context,
    }