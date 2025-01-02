import ast
import copy
import functools
import inspect
import re
import types
from typing import Callable, Dict, Optional, Tuple

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

def copy_func(func: Callable) -> Callable:
    """Create a deep copy of a function.

    Args:
        func (Callable): The function to be copied.

    Returns:
        Callable: A new function that is a deep copy of the original.
    """
    return types.FunctionType(
        func.__code__,  # Code object
        copy.copy(func.__globals__),  # Global variables
        name=func.__name__,
        argdefs=copy.copy(func.__defaults__),  # Default arguments
        closure=copy.copy(func.__closure__)  # Closure variables
    )

def add_annotations_from_docstring(func: Callable, known_types: dict = DEFAULT_KNOWN_TYPES) -> Callable:
    """Add annotations derived from Google-style docstrings to the given function.

    Args:
        func (Callable): The function to be processed.
        known_types (dict, optional): A dictionary mapping type names to Python types.

    Returns:
        Callable: The function with updated annotations.
    """
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
    


def schema_from_function(func: Callable, strict: bool = False, known_types: dict = DEFAULT_KNOWN_TYPES) -> dict:
    """Create an OpenAI-like JSON schema from a function's signature and docstring.

    Args:
        func (Callable): The function to generate the schema from.
        strict (bool, optional): Enforce strict parsing and annotation requirements.
        known_types (dict, optional): A dictionary mapping type names to Python types.

    Returns:
        dict: A JSON schema representing the function's parameters and return.
    """
    known_types = known_types.copy()
    func_name = func.__name__

    if not strict:
        # Try to add annotations from docstring
        func = add_annotations_from_docstring(func)

    copied_function = copy_func(func)
    copied_function.__annotations__ = func.__annotations__
    copied_function.__doc__ = copied_function.__doc__.replace('Arguments:\n', 'Args:\n').replace('Parameters:\n', 'Args:\n').replace('Output:\n', 'Returns:\n')

    parsed_schema = langchain.tools.base.create_schema_from_function(func_name, copied_function, parse_docstring=True).model_json_schema()

    parsed_schema = {
        'type': 'function',
        'function': {
            'name': func_name,
            'description': parsed_schema['description'],
            'parameters': {
                'type': parsed_schema['type'],
                'properties': parsed_schema['properties'],
                'required': parsed_schema['required'],
            },
        }
    }

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

                parsed_schema['function']['return'] = {
                    'type': PYTHON_TYPE_TO_JSON_SCHEMA_TYPE[return_type],
                    'description': return_description
                }
            except KeyError:
                pass

    return parsed_schema

def generate_docstring(description: str, params: Optional[Dict[str, Tuple[Optional[type], Optional[str]]]], returns: Optional[Tuple[Optional[type], Optional[str]]]) -> str:
    """
    Generate a docstring from a description, parameters, and return type.

    Args:
        description (str): The description of the function.
        params (Optional[Dict[str, Tuple[Optional[type], Optional[str]]]): A mapping of parameter names to type/description tuples.
        returns (Optional[Tuple[Optional[type], Optional[str]]]): The return type and description.
    
    Returns:
        str: The generated docstring.
    """
    docstring = description

    if params:
        docstring += '\n\nArgs:'
        for param_name, (param_type, param_description) in params.items():
            docstring += f'\n  {param_name}'

            if param_type is not None:
                docstring += f' ({param_type.__name__})'

            if param_description:
                docstring += f': {param_description}'

    if returns:
        return_type, return_description = returns
        docstring += f'\n\nReturns:\n  '

        if return_type:
            docstring += f'{return_type.__name__}'
        if return_description:
            docstring += f': {return_description}'

    return docstring

def set_params_and_annotations(name: str, docstring: str, params: Dict[str, Tuple[Optional[type], Optional[str]]], return_type: Optional[type]) -> Callable:
    """Decorator to set parameters and annotations on a function based on the given schema data.

    Args:
        name (str): The name of the function.
        docstring (str): The function's docstring.
        params (dict): A mapping of parameter names to type/description tuples.
        return_type (Optional[type]): The function's return type.

    Returns:
        Callable: The wrapped function with updated signature and docstring.
    """
    def decorator(func: Callable):
        # Create new parameters based on the provided params dict
        new_params = [
            inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=type_)
            for name, type_ in params.items()
        ]

        # Create a new signature with updated parameters and return annotation
        new_sig = inspect.Signature(parameters=new_params, return_annotation=return_type)
        
        # Define the wrapper function
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Set the new signature on the wrapper
        wrapper.__name__ = name
        wrapper.__signature__ = new_sig
        wrapper.__annotations__.update({ k: v[0] for k, v in params.items() })
        wrapper.__annotations__['return'] = return_type
        wrapper.__doc__ = docstring

        return wrapper
    return decorator
