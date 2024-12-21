import random

from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Guards import guarded_iter_unpack_sequence, guarded_unpack_sequence, full_write_guard

def execute_restricted(code, extra_globals=None, supported_imports=None, function_name='run', input_args=None, input_kwargs=None):
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
            raise Exception(f"Unsupported import {name!r}")
        return __import__(name, *args, **kwargs)

    result = None
    def register_result(x):
        nonlocal result

        if result is not None:
            raise Exception('Only one result can be registered')

        result = x

    restricted_globals =  {
        '__builtins__': {
            **safe_builtins,
            '__import__': _safe_import,
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
        **extra_globals
    }
    exec(restricted_code, restricted_globals)

    return result