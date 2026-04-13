async def contract_question_answer_node(state):
    d = {
        "answer": state["decision"].get("answer", "")
    }
    state.update(d)
    return dict(state)