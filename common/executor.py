from abc import ABC, abstractmethod
import importlib
from pathlib import Path
from typing import List
import urllib

from toolformers.base import Tool

class Executor:
    @abstractmethod
    def run_routine(self, routine_text, protocol_id, task_data, tools):
        pass

class UnsafeExecutor(Executor):
    def run_routine(self, routine_text, protocol_id, task_data, tools : List[Tool]):
        # TODO: Use routine_text
        # TODO: This should be done in a safe, containerized environment
        spec = importlib.util.spec_from_file_location(protocol_id, str(routine_path))
        loaded_module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(loaded_module)

        for tool in tools:
            loaded_module.__dict__[tool.name] = tool.as_executable_function()

        return loaded_module.run(task_data)