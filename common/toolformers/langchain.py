from typing import List

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from toolformers.base import Conversation, Tool, Toolformer, ToolLike
from langchain_core.tools import tool as function_to_tool


class LangChainConversation(Conversation):
    def __init__(self, agent : CompiledGraph, messages : List[str], category=None):
        self.agent = agent
        self.messages = messages
        self.category = category

    def chat(self, message, print_output=True) -> str:
        self.messages.append(HumanMessage(content=message))
        final_message = ''

        aggregate = None

        for chunk in self.agent.stream({'messages': self.messages}, stream_mode='values'):
            for message in chunk['messages']:
                if isinstance(message, AIMessage):
                    content = message.content
                    if isinstance(content, str):
                        final_message += content
                    else:
                        for content_chunk in content:
                            if isinstance(content_chunk, str):
                                if print_output:
                                    print(content_chunk, end='')
                                final_message += content_chunk

            aggregate = chunk if aggregate is None else (aggregate + chunk)

        if print_output:
            print()

        self.messages.append(AIMessage(content=final_message))

        return final_message
    
class LangChainToolformer(Toolformer):
    def __init__(self, model : BaseChatModel):
        self.model = model
    
    def new_conversation(self, prompt : str, tools : List[ToolLike], category=None):
        tools = [Tool.from_toollike(tool) for tool in tools]
        tools = [function_to_tool(tool.as_annotated_function()) for tool in tools]
        agent_executor = create_react_agent(self.model, tools)
        
        return LangChainConversation(agent_executor, [SystemMessage(prompt)], category)