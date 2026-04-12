CLASSIFICATION_SYSTEM = \
"""
Ты - интеллектуальный юридический ассистент.
"""

CLASSIFICATION_PROMPT = \
"""
Запрос пользователя:
{raw_input}
Классифицируй запрос пользователя. Есть только 2 класса:
1. generation - генерация документа по данным пользователя;
2. question - ответ на вопрос пользователя по документам.
Верни только одно слово - название класса (generation | question).
"""


def make_classification_dict(raw_input):
    return {
        "raw_input": raw_input,
    }