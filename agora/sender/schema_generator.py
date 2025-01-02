import json
import inspect
from typing import Callable

from agora.common.core import TaskSchema
from agora.common.toolformers.base import Toolformer

SCHEMA_GENERATOR_PROMPT = '''
You are TaskSchemaGeneratorGPT. Your task is to convert a description of a task into a standardized schema.
The final schema is a JSON object that describes the input and output of the task.
It has the following fields:
- description (string): A description of the task.
- input (object): A JSON object that describes the input of the task as a classic JSON schema object (i.e. it has the fields type, properties, etc.).
- output (object): A JSON object that describes the output of the task as a classic JSON schema object (i.e. it has the fields type, properties, etc.).

Some rules:
- All fields are required. Do not add any additional fields.
- If the description is not clear, instead of asking for more information, make educated guesses.
- Never ask for additional information.
{EXTRA_RULES}

Reply with the schema and nothing else.
'''

FROM_FUNCTION_EXTRA_RULES = '''
- If the function has type hints, use them and do not override them.
- Do not add any new input parameters.'''

class SchemaGenerator:
    """Toolformer-based task schema generation."""
    def __init__(self, toolformer: Toolformer):
        """Initialize the SchemaGenerator.

        Args:
            toolformer (Toolformer): The toolformer to use for schema generation.
        """
        self.toolformer = toolformer
    
    def _generate(self, prompt: str, message: str) -> TaskSchema:
        conversation = self.toolformer.new_conversation(prompt, [], category='schema')

        reply = conversation(message, print_output=True)

        # Extract the schema from the reply
        schema = reply[reply.find('{'):reply.rfind('}')+1]

        schema = json.loads(schema)

        return TaskSchema.from_json(schema)


    def from_function(self, func: Callable) -> TaskSchema:
        """Generate a TaskSchema schema from a function.
        Unlike TaskSchema.from_function, this method supports generating schemas from functions without type hints.

        Args:
            func (Callable): The function to generate the schema from.

        Returns:
            TaskSchema: The generated schema.
        """
        prompt = SCHEMA_GENERATOR_PROMPT.format(EXTRA_RULES=FROM_FUNCTION_EXTRA_RULES)

        message = 'Function code:\n\n' + inspect.getsource(func)

        return self._generate(prompt, message)

    def from_description(self, description: str) -> TaskSchema:
        """Generate a JSON schema from a description.

        Args:
            description (str): The description of the function.

        Returns:
            TaskSchema: The generated schema.
        """
        prompt = SCHEMA_GENERATOR_PROMPT.format(EXTRA_RULES='')

        message = 'Description:\n\n' + description

        return self._generate(prompt, message)