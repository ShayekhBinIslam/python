import contextlib

from toolformers.base import Toolformer

_default_toolformer_stack = []

@contextlib.contextmanager
def default_toolformer(toolformer: Toolformer):
    """Context manager to set the default Toolformer.

    Args:
        toolformer (Toolformer): The Toolformer instance to set as default.

    Yields:
        None
    """
    _default_toolformer_stack.append(toolformer)
    yield
    _default_toolformer_stack.pop()

def get_default_toolformer() -> Toolformer:
    """Retrieves the current default Toolformer.

    Raises:
        RuntimeError: If no default Toolformer is set.

    Returns:
        Toolformer: The current default Toolformer.
    """
    if len(_default_toolformer_stack) == 0:
        raise RuntimeError('No default toolformer set')
    return _default_toolformer_stack[-1]