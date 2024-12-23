import contextlib

from toolformers.base import Toolformer

_default_toolformer_stack = []

@contextlib.contextmanager
def default_toolformer(toolformer : Toolformer):
    _default_toolformer_stack.append(toolformer)
    yield
    _default_toolformer_stack.pop()

def get_default_toolformer():
    if len(_default_toolformer_stack) == 0:
        raise RuntimeError('No default toolformer set')
    return _default_toolformer_stack[-1]