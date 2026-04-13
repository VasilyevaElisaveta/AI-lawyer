async def contract_question_answer_node(state):
    d = {
        "response_to_user": state["decision"].get("answer", "")
    }
    state.update(d)
    return dict(state)