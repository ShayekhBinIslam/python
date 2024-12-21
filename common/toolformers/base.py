from abc import ABC, abstractmethod
import ast
import copy
import inspect
import re
import types
from typing import Callable, List, Optional, TypeAlias

from common.core import Conversation

import langchain.tools.base

DEFAULT_KNOWN_TYPES = {
    'int': int,
    'str': str,
    'bool': bool,
    'float': float,
    'list': list,
    'dict': dict
}

PYTHON_TYPE_TO_JSON_SCHEMA_TYPE = {
    int: 'integer',
    str: 'string',
    bool: 'boolean',
    float: 'number',
    list: 'array',
    dict: 'object'
}

def copy_func(func):
    """Create a deepcopy of a function."""
    return types.FunctionType(
        func.__code__,  # Code object
        copy.copy(func.__globals__),  # Global variables
        name=func.__name__,
        argdefs=copy.copy(func.__defaults__),  # Default arguments
        closure=copy.copy(func.__closure__)  # Closure variables
    )

def add_annotations_from_docstring(func, known_types=DEFAULT_KNOWN_TYPES):
    known_types = known_types.copy()

    # Get the source code of the function
    source = inspect.getsource(func)

    # Count the left whitespace of the first line
    left_whitespace = len(source) - len(source.lstrip())

    # Dedent the source code
    source = '\n'.join([line[left_whitespace:] for line in source.split('\n')])

    # Parse it into an AST
    tree = ast.parse(source)

    func_def = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func.__name__:
            func_def = node
            break

    if func_def is None:
        raise ValueError(f"Could not find function definition for {func.__name__}")

    # Extract the docstring
    docstring = ast.get_docstring(func_def)
    if not docstring:
        return func  # No docstring, nothing to do

    # Parse the docstring for Google-style Args and Returns
    # Example format:
    # Args:
    #     param1 (int): Description
    #     param2 (str): Description
    #
    # Returns:
    #     bool: Description
    #
    args_pattern = r"^\s*(\w+)\s*\(([^)]+)\):"

    lines = docstring.split('\n')
    arg_section_found = False
    return_section_found = False
    doc_args = {}
    doc_return_type = None

    for i, line in enumerate(lines):
        # Detect start of Args section
        if line.strip().lower().startswith("args:"):
            arg_section_found = True
            continue
        # Detect start of Returns section
        if line.strip().lower().startswith("returns:"):
            return_section_found = True
            arg_section_found = False  # end args
            continue

        if arg_section_found:
            # If we reach a blank line or next section, stop args capture
            if not line.strip() or line.strip().lower().startswith("returns:"):
                arg_section_found = False
            else:
                match = re.match(args_pattern, line)
                if match:
                    param_name, param_type = match.groups()
                    doc_args[param_name] = param_type.strip()

        if return_section_found:
            # Extract the return line
            stripped = line.strip()
            if stripped:
                # If there's a colon, assume the format "Type: description"
                colon_pos = stripped.find(':')
                if colon_pos != -1:
                    doc_return_type = stripped[:colon_pos].strip()
                else:
                    # If no colon, assume entire line is the type, but only if the type is among known types
                    if stripped in known_types:
                        doc_return_type = stripped
                return_section_found = False

    # Update annotations
    current_annotations = dict(func.__annotations__)
    func_signature = inspect.signature(func)

    def resolve_type(type_str):
        # Return a Python type if known, otherwise leave as a string
        return known_types.get(type_str, type_str)

    # Update parameter annotations
    for param in func_signature.parameters.values():
        if param.name in doc_args and param.name not in current_annotations:
            ann_type = resolve_type(doc_args[param.name])
            current_annotations[param.name] = ann_type

    # Update return annotation if missing
    if doc_return_type and "return" not in current_annotations:
        ann_return_type = resolve_type(doc_return_type)
        current_annotations["return"] = ann_return_type

    wrapper = copy_func(func)
    wrapper.__annotations__ = current_annotations

    return wrapper
    


def schema_from_function(func: Callable, strict=False, known_types=DEFAULT_KNOWN_TYPES):
    known_types = known_types.copy()
    func_name = func.__name__


    if not strict:
        # Try to add annotations from docstring
        func = add_annotations_from_docstring(func)

    # TODO: Best-effort non-destructive Arguments -> Args, Parameters -> Args, Output -> Returns

    parsed_schema = langchain.tools.base.create_schema_from_function(func_name, func, parse_docstring=True).model_json_schema()

    if 'Returns:' in func.__doc__:
        returns = func.__doc__.split('Returns:')[1].strip()

        if returns:
            # If there's a colon, assume the format "Type: description"
            colon_pos = returns.find(':')
            if colon_pos != -1:
                return_description = returns[colon_pos + 1:].strip()
            else:
                # If no colon, assume entire line is the description, but only if it's not in the known types
                if returns not in known_types:
                    return_description = returns

            try:
                if 'return' not in func.__annotations__ and strict:
                    raise ValueError(f"Return type not found in annotations for function {func_name}")
                
                return_type = func.__annotations__.get('return', str)

                if return_type not in PYTHON_TYPE_TO_JSON_SCHEMA_TYPE:
                    raise ValueError(f"Return type {return_type} not supported in JSON schema")

                parsed_schema['returns'] = {
                    'type': PYTHON_TYPE_TO_JSON_SCHEMA_TYPE[return_type],
                    'description': return_description
                }
            except KeyError:
                pass


    return parsed_schema


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

