from abc import abstractmethod
import importlib
from typing import Any, List

from common.toolformers.base import Tool, Conversation
from common.interpreters.restricted import execute_restricted

class Executor:
    """Abstract base class for executors that run protocol implementations."""

    @abstractmethod
    def __call__(
        self,
        protocol_id: str,
        code: str,
        tools: List[Tool],
        input_args: list,
        input_kwargs: dict
    ) -> Any:
        """Executes code with provided tools and arguments.

        Args:
            protocol_id (str): The protocol identifier.
            code (str): The code to execute.
            tools (List[Tool]): Available tools for the code.
            input_args (list): Positional arguments.
            input_kwargs (dict): Keyword arguments.

        Returns:
            Any: The result of the code execution.
        """
        pass

    def new_conversation(
        self,
        protocol_id: str,
        code: str,
        multiround: bool,
        tools: List[Tool]
    ) -> Conversation:
        """Starts a new conversation using the executor.

        Args:
            protocol_id (str): The protocol identifier.
            code (str): The code to execute.
            multiround (bool): Whether multiple rounds are allowed.
            tools (List[Tool]): Tools allowed for execution.

        Returns:
            Conversation: A conversation object for execution.
        """
        return ExecutorConversation(self, protocol_id, code, multiround, tools)

class UnsafeExecutor(Executor):
    """Executes code in an unsafe environment, allowing unrestricted operations."""

    def __call__(
        self,
        protocol_id: str,
        code: str,
        tools: List[Tool],
        input_args: list,
        input_kwargs: dict
    ) -> Any:
        """Executes code using Python's importlib without restrictions.

        Args:
            protocol_id (str): The protocol identifier.
            code (str): The code to execute.
            tools (List[Tool]): Tools available to the executed code.
            input_args (list): Positional arguments.
            input_kwargs (dict): Keyword arguments.

        Returns:
            Any: The result of the executed code.
        """
        protocol_id = protocol_id.replace('-', '_').replace('.', '_').replace('/', '_')
        spec = importlib.util.spec_from_loader(protocol_id, loader=None)
        loaded_module = importlib.util.module_from_spec(spec)

        exec(code, loaded_module.__dict__)

        for tool in tools:
            loaded_module.__dict__[tool.name] = tool.func

        return loaded_module.run(*input_args, **input_kwargs)
    
class RestrictedExecutor(Executor):
    """Executes code in a restricted environment to ensure safety."""

    def __call__(
        self,
        protocol_id: str,
        code: str,
        tools: List[Tool],
        input_args: list,
        input_kwargs: dict
    ) -> Any:
        """Executes the code using a restricted interpreter with limited globals.

        Args:
            protocol_id (str): The protocol identifier.
            code (str): The code to execute.
            tools (List[Tool]): Tools allowed in the environment.
            input_args (list): Positional arguments for the function.
            input_kwargs (dict): Keyword arguments for the function.

        Returns:
            Any: The result of the execution.
        """
        supported_globals = {
            tool.name : tool.func for tool in tools
        }
        return execute_restricted(code, supported_imports=['json'], function_name='run', extra_globals=supported_globals, input_args=input_args, input_kwargs=input_kwargs)


class ExecutorConversation(Conversation):
    """Handles conversations by executing code via the associated executor."""

    def __init__(
        self,
        executor: Executor,
        protocol_id: str,
        code: str,
        multiround: bool,
        tools: List[Tool]
    ) -> None:
        """Initializes ExecutorConversation.

        Args:
            executor (Executor): The executor used for code execution.
            protocol_id (str): The identifier of the protocol.
            code (str): The code to be executed.
            multiround (bool): Whether multiple rounds are allowed.
            tools (List[Tool]): Tools allowed for execution.
        """
        self.executor = executor
        self.protocol_id = protocol_id
        self.code = code
        self.multiround = multiround
        self.tools = tools
        self.memory = {} if multiround else None
    
    def __call__(self, message: str, print_output: bool = True) -> Any:
        """Processes a message by executing the implementation code.

        Args:
            message (str): The input message for the conversation.
            print_output (bool): Whether to print the result.

        Returns:
            Any: The output from the execution of the code.
        """
        if self.multiround:
            response, self.memory = self.executor(self.protocol_id, self.code, self.tools, [message, dict(self.memory)], {})
        else:
            response = self.executor(self.protocol_id, self.code, self.tools, [message], {})

        if print_output:
            print(response)
        
        return response