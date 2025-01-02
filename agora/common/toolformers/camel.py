from typing import List, Optional, TYPE_CHECKING

from agora.common.toolformers.base import Conversation, Toolformer, Tool, ToolLike

if TYPE_CHECKING:
    import camel.messages
    import camel.models
    import camel.agents
    import camel.toolkits.function_tool
    import camel.types

try:
    import camel.messages
    import camel.models
    import camel.agents
    import camel.toolkits.function_tool
    import camel.types
    CAMEL_IMPORT_ERROR = None
except ImportError as e:
    CAMEL_IMPORT_ERROR = e

class CamelConversation(Conversation):
    """Handles conversations using the Camel AI Toolformer."""

    def __init__(self, toolformer: 'CamelToolformer', agent: 'camel.agents.ChatAgent', category: Optional[str] = None) -> None:
        """Initialize the CamelConversation with a Toolformer and ChatAgent.

        Args:
            toolformer (CamelToolformer): The CamelToolformer instance managing the conversation.
            agent (ChatAgent): The ChatAgent handling the conversation logic.
            category (Optional[str], optional): The category of the conversation. Defaults to None.

        Raises:
            ImportError: If camel-ai is not available.
        """

        if CAMEL_IMPORT_ERROR:
            raise CAMEL_IMPORT_ERROR

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
        formatted_message = camel.messages.BaseMessage.make_user_message('user', message)
        
        response = self.agent.step(formatted_message)

        reply = response.msg.content

        if print_output:
            print(reply)
        
        return reply

class CamelToolformer(Toolformer):
    """Toolformer implementation using the Camel AI framework."""

    def __init__(self, model_platform: 'camel.types.ModelPlatformType', model_type: 'camel.types.ModelType', model_config_dict: dict, name: Optional[str] = None) -> None:
        """Initialize the CamelToolformer with model details.

        Args:
            model_platform (ModelPlatformType): The platform of the model (e.g. "openai").
            model_type (ModelPlatformType): The type of the model (e.g. "gpt-4o").
            model_config_dict (dict): Configuration dictionary for the model.
            name (Optional[str], optional): Optional name for the Toolformer. Defaults to None.

        Raises:
            ImportError: If camel-ai is not available.
        """

        if CAMEL_IMPORT_ERROR:
            raise CAMEL_IMPORT_ERROR

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
        model = camel.models.ModelFactory.create(
            model_platform=self.model_platform,
            model_type=self.model_type,
            model_config_dict=dict(self.model_config_dict)
        )

        tools = [Tool.from_toollike(tool) for tool in tools]

        agent = camel.agents.ChatAgent(
            model=model,
            system_message=camel.messages.BaseMessage.make_assistant_message('system', prompt),
            tools=[camel.toolkits.function_tool.FunctionTool(tool.func, openai_tool_schema=tool.openai_schema) for tool in tools]
        )

        return CamelConversation(self, agent, category)
