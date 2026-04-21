from langchain_core.messages import BaseMessage


class TokenCounter:

    def __init__(self, llm):
        self.llm = llm

    def count_messages_tokens(
        self,
        messages: list[BaseMessage],
    ) -> int:

        return self.llm.get_num_tokens_from_messages(
            messages
        )