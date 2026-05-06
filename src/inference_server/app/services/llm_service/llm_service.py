from langchain.prompts import ChatPromptTemplate

from .prompts import CHAT_NAME_PROMPT, CHAT_NAME_SYSTEM

from .....agents.llm_client import create_gigachat


class LLMService:
    def __init__(self, model, **kwargs):
        self.llm = create_gigachat(model, **kwargs)
    
    async def aget_chat_name(self, raw_input, config=None):
        input_d = {
            "raw_input": raw_input,
        }
        prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_NAME_SYSTEM),
            ("human", CHAT_NAME_PROMPT)
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke(input_d, config=config)
        raw = response.content
        return raw