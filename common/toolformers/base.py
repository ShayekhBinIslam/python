from abc import ABC, abstractmethod
import json
from typing import Callable, List, Optional, TypeAlias

from common.core import Conversation
from common.function_schema import DEFAULT_KNOWN_TYPES, PYTHON_TYPE_TO_JSON_SCHEMA_TYPE, schema_from_function, generate_docstring, set_params_and_annotations


class Tool:
    def __init__(self, name: str, description: str, args_schema: dict, return_schema: dict, func: Callable):
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.return_schema = return_schema
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
        return_schema: dict = None,
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
    def _args_schema_parsed(self):
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
    def _return_schema_parsed(self):
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
    def docstring(self):
        return generate_docstring(self.description, self._args_schema_parsed, self._return_schema_parsed)

    def __str__(self):
        return f'Tool({self.name})\n' + self.docstring

    def as_documented_python(self):
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

    def as_annotated_function(self):
        return set_params_and_annotations(self.name, self.docstring, self._args_schema_parsed, self._return_schema_parsed)(self.func)
        

ToolLike: TypeAlias = Callable | Tool

class Toolformer(ABC):
    @abstractmethod
    def new_conversation(self, prompt : str, tools : List[ToolLike], category : Optional[str] = None) -> Conversation:
        pass

