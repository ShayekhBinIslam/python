from abc import ABC, abstractmethod
import json
from typing import Callable, List, Optional, TypeAlias

from common.core import Conversation
from common.function_schema import DEFAULT_KNOWN_TYPES, PYTHON_TYPE_TO_JSON_SCHEMA_TYPE, schema_from_function, generate_docstring, set_params_and_annotations


class Tool:
    """Represents a tool with a name, description, argument schema, return schema, and a callable function."""

    def __init__(
        self,
        name: str,
        description: str,
        args_schema: dict,
        return_schema: dict,
        func: Callable
    ) -> None:
        """Initializes the Tool.

        Args:
            name (str): The name of the tool.
            description (str): A brief description of the tool.
            args_schema (dict): JSON schema for input arguments.
            return_schema (dict): JSON schema for the return values.
            func (Callable): The function implementing the tool.
        """
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.return_schema = return_schema
        self.func = func

    @property
    def openai_schema(self) -> dict:
        """Returns the OpenAI-compatible schema of the tool.

        Returns:
            dict: The OpenAI-compatible schema.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema
            }
        }

    @staticmethod
    def from_function(
        func: Callable,
        name: str = None,
        description: str = None,
        args_schema: dict = None,
        return_schema: dict = None,
        infer_schema: bool = True,
        inference_known_types: dict = DEFAULT_KNOWN_TYPES,
        strict_inference: bool = False
    ) -> 'Tool':
        """Create a Tool instance from a given function, optionally inferring schemas.

        Args:
            func (Callable): The function to create a Tool from.
            name (str, optional): The name of the tool. Defaults to the function's name if None.
            description (str, optional): A description of the tool. Defaults to the function's docstring or schema description.
            args_schema (dict, optional): JSON schema for input arguments. If None and infer_schema is True, schema is inferred. Defaults to None.
            return_schema (dict, optional): JSON schema for return values. If None and infer_schema is True, schema is inferred. Defaults to None.
            infer_schema (bool, optional): Whether to infer schemas automatically. Defaults to True.
            inference_known_types (dict, optional): Known types for schema inference. Defaults to DEFAULT_KNOWN_TYPES.
            strict_inference (bool, optional): Whether to enforce strict schema inference. Defaults to False.

        Returns:
            Tool: A new Tool instance based on the provided function.
        
        Raises:
            ValueError: If required parameters are missing when infer_schema is False.
        """
        if infer_schema:
            schema = schema_from_function(func, known_types=inference_known_types, strict=strict_inference)

            return Tool(
                name=name or func.__name__,
                description=description or schema.get('description', func.__doc__),
                args_schema=args_schema or schema.get('properties', {}),
                return_schema=schema.get('returns', {}),
                func=func
            )
        else:
            if not infer_schema:
                if not name:
                    raise ValueError("name must be provided if infer_schema is False")
                if not description:
                    raise ValueError("description must be provided if infer_schema is False")
                if not args_schema:
                    raise ValueError("args_schema must be provided if infer_schema is False")
                if not return_schema:
                    raise ValueError("return_schema must be provided if infer_schema is False")   

            return Tool(
                name=name,
                description=description,
                args_schema=args_schema,
                return_schema=return_schema,
                func=func
            )
        
    @staticmethod
    def from_toollike(tool_like: 'ToolLike', name: Optional[str] = None, description: Optional[str] = None, args_schema: Optional[dict] = None, return_schema: Optional[dict] = None, inference_known_types: Optional[dict] = DEFAULT_KNOWN_TYPES, strict_inference: Optional[bool] = None) -> 'Tool':
        """Convert a Tool-like object into a Tool instance.

        Args:
            tool_like (ToolLike): The Tool-like object to convert.
            name (Optional[str], optional): The name of the tool. Defaults to None.
            description (Optional[str], optional): A description of the tool. Defaults to None.
            args_schema (Optional[dict], optional): JSON schema for input arguments. Defaults to None.
            return_schema (Optional[dict], optional): JSON schema for return values. Defaults to None.
            inference_known_types (Optional[dict], optional): Known types for schema inference. Defaults to DEFAULT_KNOWN_TYPES.
            strict_inference (Optional[bool], optional): Whether to enforce strict schema inference. Defaults to None.

        Returns:
            Tool: A new Tool instance based on the Tool-like object.
        
        Raises:
            ValueError: If the Tool-like object is neither a Tool nor a callable.
        """
        if isinstance(tool_like, Tool):
            return tool_like
        elif callable(tool_like):
            return Tool.from_function(
                tool_like,
                name=name,
                description=description,
                args_schema=args_schema,
                return_schema=return_schema,
                infer_schema=True,
                inference_known_types=inference_known_types,
                strict_inference=strict_inference
            )
        else:
            raise ValueError("Tool-like object must be either a Tool or a callable")

    @property
    def _args_schema_parsed(self) -> dict:
        """Parse the argument schema into a structured format.

        Returns:
            dict: A dictionary mapping argument names to their types and descriptions.
        """
        inverted_types = {v: k for k, v in PYTHON_TYPE_TO_JSON_SCHEMA_TYPE.items()}
        params = {}

        for arg_name, arg_schema in self.args_schema.items():
            arg_type = inverted_types[arg_schema['type']]
            arg_description = arg_schema.get('description', '')

            if arg_schema['type'] == 'object':
                arg_description = arg_description.strip()

                if arg_description and not arg_description.endswith('.'):
                    arg_description += '.'

                arg_description += ' Schema:' + json.dumps(arg_schema)
                arg_description = arg_description.strip()

            params[arg_name] = (arg_type, arg_description)

        return params

    @property
    def _return_schema_parsed(self) -> Optional[tuple]:
        """Parse the return schema into a structured format.

        Returns:
            Optional[tuple]: A tuple containing the return type and its description, or None if no return schema is present.
        """
        inverted_types = {v: k for k, v in PYTHON_TYPE_TO_JSON_SCHEMA_TYPE.items()}
        if self.return_schema:
            return_type = inverted_types[self.return_schema['type']]

            return_description = self.return_schema.get('description', '')

            if self.return_schema['type'] == 'object':
                return_description = return_description.strip()
                if return_description and not return_description.endswith('.'):
                    return_description += '.'

                return_description += ' Schema: ' + json.dumps(self.return_schema)
                return_description = return_description.strip()

            return (return_type, return_description)

        return None

    @property
    def docstring(self) -> str:
        """Generate a docstring for the tool based on its description and schemas.

        Returns:
            str: The generated docstring.
        """
        return generate_docstring(self.description, self._args_schema_parsed, self._return_schema_parsed)

    def __str__(self) -> str:
        """Return the string representation of the Tool.

        Returns:
            str: The string representation.
        """
        return f'Tool({self.name})\n' + self.docstring

    def as_documented_python(self) -> str:
        """Export the tool as a documented Python function.

        Returns:
            str: The Python function code as a string with documentation.
        """
        inverted_types = {v: k for k, v in PYTHON_TYPE_TO_JSON_SCHEMA_TYPE.items()}

        s = f'def {self.name}('

        signature_args = []

        for arg_name, arg_schema in self.args_schema.items():
            arg_type = inverted_types[arg_schema['type']].__name__
            signature_args.append(f'{arg_name}: {arg_type}')

        s += ', '.join(signature_args)
        s += '):\n'

        s += self.docstring

        return s

    def as_annotated_function(self) -> Callable:
        """Return the tool as an annotated function.

        Returns:
            Callable: The annotated function.
        """
        return set_params_and_annotations(self.name, self.docstring, self._args_schema_parsed, self._return_schema_parsed)(self.func)
        

ToolLike: TypeAlias = Callable | Tool

class Toolformer(ABC):
    """Abstract base class for Toolformers, which manage conversations with tools."""

    @abstractmethod
    def new_conversation(self, prompt: str, tools: List[ToolLike], category: Optional[str] = None) -> Conversation:
        """Starts a new conversation with the given prompt and tools.

        Args:
            prompt (str): The initial prompt for the conversation.
            tools (List[ToolLike]): Tools to be available in the conversation.
            category (Optional[str]): The category of the conversation.

        Returns:
            Conversation: A Conversation instance managing the interaction.
        """
        pass

