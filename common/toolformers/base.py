from abc import ABC, abstractmethod
import ast
import copy
import inspect
import re
import types
from typing import Callable, List, Optional, TypeAlias

from common.core import Conversation
from common.function_schema import DEFAULT_KNOWN_TYPES, PYTHON_TYPE_TO_JSON_SCHEMA_TYPE, schema_from_function

import langchain.tools.base




class Tool:
    def __init__(self, name: str, description: str, args_schema: dict, returns_schema: dict, func: Callable):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.returns_schema = returns_schema
        self.func = func

    @property
    def openai_schema(self):
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
        returns_schema: dict = None,
        infer_schema: bool = True,
        inference_known_types: dict = DEFAULT_KNOWN_TYPES,
        strict_inference: bool = False
    ):
        if infer_schema:
            schema = schema_from_function(func, known_types=inference_known_types, strict=strict_inference)

            return Tool(
                name=name or func.__name__,
                description=description or schema.get('description', func.__doc__),
                args_schema=args_schema or schema.get('properties', {}),
                returns_schema=schema.get('returns', {}),
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
                if not returns_schema:
                    raise ValueError("returns_schema must be provided if infer_schema is False")   

            return Tool(
                name=name,
                description=description,
                args_schema=args_schema,
                returns_schema=returns_schema,
                func=func
            )
        
    @staticmethod
    def from_toollike(tool_like: 'ToolLike') -> 'Tool':
        # TODO: Support overrides
        # TODO: Support Camel and LangChain tools
        if isinstance(tool_like, Tool):
            return tool_like
        elif callable(tool_like):
            return Tool.from_function(tool_like)
        else:
            raise ValueError("Tool-like object must be either a Tool or a callable")
    
    def __str__(self):
        s = f'Tool({self.name})\n{self.description}\n'

        inverted_types = {v: k for k, v in PYTHON_TYPE_TO_JSON_SCHEMA_TYPE.items()}

        if len(self.args_schema) == 0:
            s += '\nNo arguments.'
        else:
            s += '\nArguments:\n'
            for arg_name, arg_schema in self.args_schema.items():
                arg_type = inverted_types[arg_schema['type']].__name__
                s += f'    {arg_name} ({arg_type}): {arg_schema["description"]}\n'

        if self.returns_schema:
            return_type = inverted_types[self.returns_schema['type']].__name__
            s += f'\nReturns:\n    {return_type}: {self.returns_schema["description"]}'
        
        return s

ToolLike: TypeAlias = Callable | Tool

class Toolformer(ABC):
    @abstractmethod
    def new_conversation(self, prompt : str, tools : ToolLike, category : Optional[str] = None) -> Conversation:
        pass

