from ....utils import messages_to_str, documents_to_str


async def question_intake_node(state):
    """
    Используется в случаях, если агенту по договорам задали какой-либо вопрос, а не дали задание на генерацию документа.
    Собирает и валидирует необходимые поля из state.
    """
    messages = state.get("messages", [])
    messages_str = messages_to_str(messages)
    summarized_documents = state.get("summarized_documents", [])
    summarized_documents_str = documents_to_str(summarized_documents)
    d = {
        "messages_str": messages_str,
        "summarized_documents_str": summarized_documents_str
    }
    state.update(d)
    return dict(state)