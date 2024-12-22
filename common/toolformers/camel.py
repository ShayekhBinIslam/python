from typing import List

from common.toolformers.base import Conversation, Toolformer, Tool, ToolLike
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.messages import BaseMessage as bm
from camel.agents import ChatAgent
from camel.toolkits.function_tool import FunctionTool

class CamelConversation(Conversation):
    def __init__(self, toolformer : 'CamelToolformer', agent : ChatAgent, category=None):
        self.toolformer = toolformer
        self.agent = agent
        self.category = category
    
    def __call__(self, message, print_output=True):
        formatted_message = BaseMessage.make_user_message('user', message)
        
        response = self.agent.step(formatted_message)

        reply = response.msg.content

        if print_output:
            print(reply)
        
        return reply

class CamelToolformer(Toolformer):
    def __init__(self, model_platform, model_type, model_config_dict, name=None):
        self.model_platform = model_platform
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self._name = name

    @property
    def name(self):
        if self._name is None:
            return f'{self.model_platform.value}_{self.model_type.value}'
        else:
            return self._name

    def new_conversation(self, prompt : str, tools : List[ToolLike], category=None) -> Conversation:
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
