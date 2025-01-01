from typing import List, Optional

from common.toolformers.base import Conversation, Toolformer, Tool, ToolLike
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.messages import BaseMessage as bm
from camel.agents import ChatAgent
from camel.toolkits.function_tool import FunctionTool

class CamelConversation(Conversation):
    """Handles conversations using the Camel AI Toolformer."""

    def __init__(self, toolformer: 'CamelToolformer', agent: ChatAgent, category: Optional[str] = None) -> None:
        """Initialize the CamelConversation with a Toolformer and ChatAgent.

        Args:
            toolformer (CamelToolformer): The CamelToolformer instance managing the conversation.
            agent (ChatAgent): The ChatAgent handling the conversation logic.
            category (Optional[str], optional): The category of the conversation. Defaults to None.
        """
        self.toolformer = toolformer
        self.agent = agent
        self.category = category
    
    def __call__(self, message: str, print_output: bool = True) -> str:
        """Process a message within the conversation and return the response.

        Args:
            message (str): The message to process.
            print_output (bool, optional): Whether to print the response. Defaults to True.

        Returns:
            str: The response from the conversation.
        """
        formatted_message = BaseMessage.make_user_message('user', message)
        
        response = self.agent.step(formatted_message)

        reply = response.msg.content

        if print_output:
            print(reply)
        
        return reply

class CamelToolformer(Toolformer):
    """Toolformer implementation using the Camel AI framework."""

    def __init__(self, model_platform, model_type, model_config_dict: dict, name: Optional[str] = None) -> None:
        """Initialize the CamelToolformer with model details.

        Args:
            model_platform: The platform of the model.
            model_type: The type of the model.
            model_config_dict (dict): Configuration dictionary for the model.
            name (Optional[str], optional): Optional name for the Toolformer. Defaults to None.
        """
        self.model_platform = model_platform
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self._name = name

    @property
    def name(self) -> str:
        """Get the name of the Toolformer.

        Returns:
            str: The name of the Toolformer.
        """
        if self._name is None:
            return f'{self.model_platform.value}_{self.model_type.value}'
        else:
            return self._name

    def new_conversation(self, prompt: str, tools: List[ToolLike], category: Optional[str] = None) -> Conversation:
        """Start a new conversation with the given prompt and tools.

        Args:
            prompt (str): The initial prompt for the conversation.
            tools (List[ToolLike]): A list of tools to be available in the conversation.
            category (Optional[str], optional): The category of the conversation. Defaults to None.

        Returns:
            Conversation: A Conversation instance managing the interaction.
        """
        model = ModelFactory.create(
            model_platform=self.model_platform,
            model_type=self.model_type,
            model_config_dict=dict(self.model_config_dict)
        )

        tools = [Tool.from_toollike(tool) for tool in tools]

        agent = ChatAgent(
            model=model,
            system_message=bm.make_assistant_message('system', prompt),
            tools=[FunctionTool(tool.func, openai_tool_schema=tool.openai_schema) for tool in tools]
        )

        return CamelConversation(self, agent, category)
