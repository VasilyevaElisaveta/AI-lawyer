from langchain_core.prompts import ChatMessagePromptTemplate


async def question_answer_node(state, llm):
    """
    Собирает промпт из полученных данных, отправляет его LLM, получает ответ от неё и добавляет его в state.
    """
    d = {
        "answer": state["decision"].get("answer", "")
    }
    state.update(d)
    return dict(state)