from typing import List, Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from agora.common.toolformers.base import Conversation, Tool, Toolformer, ToolLike
from langchain_core.tools import tool as function_to_tool


class LangChainConversation(Conversation):
    def __init__(self, agent: CompiledGraph, messages: List[str], category: Optional[str] = None) -> None:
        """Initializes a LangChainConversation instance.

        Args:
            agent (CompiledGraph): The compiled LangChain agent to process messages.
            messages (List[str]): The conversation history.
            category (Optional[str], optional): An optional category or tag for the conversation.
        """
        self.agent = agent
        self.messages = messages
        self.category = category

    def chat(self, message: str, print_output: bool = True) -> str:
        """Sends a message to the conversation and returns the AI response.

        Args:
            message (str): The user message or query.
            print_output (bool, optional): Whether to print the AI response as it streams.

        Returns:
            str: The concatenated AI response.
        """
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
    def __init__(self, model: BaseChatModel):
        """Initializes a LangChainToolformer.

        Args:
            model (BaseChatModel): The underlying language model for processing.
        """
        self.model = model
    
    def new_conversation(self, prompt: str, tools: List[ToolLike], category: Optional[str] = None) -> Conversation:
        """Creates a new conversation using the provided prompt and tools.

        Args:
            prompt (str): The initial conversation prompt.
            tools (List[ToolLike]): Tools available to the conversation.
            category (Optional[str], optional): A category or tag for this conversation.

        Returns:
            Conversation: The conversation instance using the specified tools.
        """
        tools = [Tool.from_toollike(tool) for tool in tools]
        tools = [function_to_tool(tool.as_annotated_function()) for tool in tools]
        agent_executor = create_react_agent(self.model, tools)
        
        return LangChainConversation(agent_executor, [SystemMessage(prompt)], category)