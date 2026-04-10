from ....utils import messages_to_str


async def question_intake_node(state):
    """
    Используется в случаях, если агенту по договорам задали какой-либо вопрос, а не дали задание на генерацию документа.
    Собирает и валидирует необходимые поля из state.
    """
    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}
    summarized_data = state.get("conversation_summary", "")
    if not summarized_data:
        print("conversation_summary not in state")
    messages = state.get("messages", [])
    messages_str = messages_to_str(messages)