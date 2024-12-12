from abc import abstractmethod
import importlib
from typing import List

from toolformers.base import Tool, Conversation

class Executor:
    @abstractmethod
    def __call__(self, protocol_id, code, task_data, tools : List[Tool]):
        pass

    def new_conversation(self, protocol_id : str, code : str, tools : List[Tool]) -> Conversation:
        return ExecutorConversation(self, protocol_id, code, tools)

class UnsafeExecutor(Executor):
    def __call__(self, protocol_id, code, task_data, tools : List[Tool]):
        print(code)
        protocol_id = protocol_id.replace('-', '_').replace('.', '_').replace('/', '_')
        # TODO: This should be done in a safe, containerized environment
        spec = importlib.util.spec_from_loader(protocol_id, loader=None)
        loaded_module = importlib.util.module_from_spec(spec)

        exec(code, loaded_module.__dict__)

        for tool in tools:
            loaded_module.__dict__[tool.name] = tool.as_executable_function()

        return loaded_module.run(task_data)

class ExecutorConversation(Conversation):
    def __init__(self, executor : Executor, protocol_id : str, code : str, tools : List[Tool]):
        self.executor = executor
        self.protocol_id = protocol_id
        self.code = code
        self.tools = tools
    
    def __call__(self, message, print_output=True):
        # TODO: Support multiround conversations
        response = self.executor(self.protocol_id, self.code, message, self.tools)

        if print_output:
            print(response)
        
        return response