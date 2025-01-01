import random
from typing import Any, Optional, List

from RestrictedPython import compile_restricted, safe_builtins, limited_builtins, utility_builtins
from RestrictedPython.Guards import guarded_iter_unpack_sequence, guarded_unpack_sequence, full_write_guard

from agora.common.errors import ExecutionError

def execute_restricted(
    code: str,
    extra_globals: Optional[dict] = None,
    supported_imports: Optional[List[str]] = None,
    function_name: str = 'run',
    input_args: Optional[List[Any]] = None,
    input_kwargs: Optional[dict] = None
) -> Any:
    """Executes restricted code with limited globals and supported imports.

    Args:
        code (str): The code to execute.
        extra_globals (Optional[dict]): Additional global variables.
        supported_imports (Optional[List[str]]): List of allowed modules.
        function_name (str): The name of the function to execute.
        input_args (Optional[List[Any]]): Positional arguments for the function.
        input_kwargs (Optional[dict]): Keyword arguments for the function.

    Returns:
        Any: The result of the executed function.

    Raises:
        ExecutionError: If an unsupported import is attempted or multiple results are registered.
    """
    extra_globals = extra_globals or {}
    supported_imports = supported_imports or []
    input_args = input_args or []
    input_kwargs = input_kwargs or {}
    
    register_function_name = 'register_' + str(random.randint(0, 1000000))    
    get_parameters_name = 'get_parameters_' + str(random.randint(0, 1000000))

    def get_parameters():
        return input_args, input_kwargs
    
    code += f'''
input_args, input_kwargs = {get_parameters_name}()
{register_function_name}({function_name}(*input_args, **input_kwargs))'''

    restricted_code = compile_restricted(code, '<string>', 'exec')

    _SAFE_MODULES = frozenset(supported_imports)

    def _safe_import(name, *args, **kwargs):
        if name not in _SAFE_MODULES:
            raise ExecutionError(f"Unsupported import {name!r}")
        return __import__(name, *args, **kwargs)

    result = None
    def register_result(x):
        nonlocal result

        if result is not None:
            raise ExecutionError('Only one result can be registered')

        result = x

    restricted_globals =  {
        '__builtins__': {
            **safe_builtins,
            **limited_builtins,
            **utility_builtins,
            '__import__': _safe_import
        },
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        '_unpack_sequence_': guarded_unpack_sequence,
        '_getiter_': iter,
        '_print_': print,
        '_apply_': lambda f, *args, **kwargs: f(*args, **kwargs),
        '_getitem_': lambda obj, key: obj[key],
        '_write_': full_write_guard,
        get_parameters_name: get_parameters,
        register_function_name: register_result,
        'map': map,
        'list': list,
        'dict': dict,
        **extra_globals
    }
    exec(restricted_code, restricted_globals)

    return result