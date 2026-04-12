from langchain_core.prompts import ChatPromptTemplate

from .promtps import ADDITION_PROMPT, ADDITION_SYSTEM, make_addition_prompt

from ....utils import safe_parse_list_int


async def question_addition_node(state, llm):
    """
    Определяет, необходимо ли к основному промпту для LLM добавить информацию о каких-либо сгенерированных договорах пользователя до этого.
    Если такие документы есть, то информация их них добавляется в state.
    """
    raw_input = state.get("raw_input", "")
    if not raw_input:
        return {"error": "Нет входных данных. Передайте raw_input или input_data."}
    conversation_summary = state.get("conversation_summary", "")
    if not conversation_summary:
        print("conversation_summary not in state")
    messages_str = state.get("messages_str", "")
    if not messages_str:
        print("messages_str not in state")
    summarized_documents_str = state.get("summarized_documents_str", "")
    if not summarized_documents_str:
        print("summarized_documents_str not in state")

    input_d = make_addition_prompt(raw_input, messages_str, summarized_documents_str)
    prompt = ChatPromptTemplate.from_messages(
        ("system", ADDITION_SYSTEM)
        ("human", ADDITION_PROMPT)
    )

    chain = prompt | llm

    result = chain.ainvoke(input_d)
    indexes = safe_parse_list_int(result.get("content", ""))
    d = {
        "documents_indexes": indexes
    }
    state.update(d)
    return dict(state)
