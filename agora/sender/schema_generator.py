import json
import inspect
from typing import Callable

from agora.sender.task_schema import TaskSchema
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

class TaskSchemaGenerator:
    """Toolformer-based task schema generation."""
    def __init__(self, toolformer: Toolformer):
        """Initialize the SchemaGenerator.

        Args:
            toolformer (Toolformer): The toolformer to use for schema generation.
        """
        self.toolformer = toolformer
    
    def _generate(self, prompt: str, message: str, description: str = None, input_schema: dict = None, output_schema: dict = None) -> TaskSchema:
        if description is not None and input_schema is None and output_schema is None:
            # We can generate the schema directly
            return TaskSchema(description, input_schema, output_schema)

        # We inform the toolformer of the overrides, since they can be useful to generate the rest of the schema
        if description is not None:
            message += '\n\n' + 'Description override:\n\n' + description

        if input_schema is not None:
            message += '\n\n' + 'Input schema override:\n\n' + json.dumps(input_schema, indent=2)

        if output_schema is not None:
            message += '\n\n' + 'Output schema override:\n\n' + json.dumps(output_schema, indent=2)

        conversation = self.toolformer.new_conversation(prompt, [], category='schema')

        reply = conversation(message, print_output=True)

        # Extract the schema from the reply
        schema = reply[reply.find('{'):reply.rfind('}')+1]

        schema = json.loads(schema)

        if description is not None:
            schema['description'] = description
        
        if input_schema is not None:
            schema['input_schema'] = input_schema

        if output_schema is not None:
            schema['output_schema'] = output_schema

        return TaskSchema.from_json(schema)


    def from_function(self, func: Callable, description: str = None, input_schema: dict = None, output_schema: dict = None) -> TaskSchema:
        """Generate a TaskSchema schema from a function.
        Unlike TaskSchema.from_function, this method supports generating schemas from functions without type hints.

        Args:
            func (Callable): The function to generate the schema from.
            description (str, optional): If not None, overrides the generated description. Defaults to None.
            input_schema (dict, optional): If not None, overrides the generated input schema. Defaults to None.
            output_schema (dict, optional): If not None, overrides the generated output schema. Defaults to None.

        Returns:
            TaskSchema: The generated schema.
        """
        prompt = SCHEMA_GENERATOR_PROMPT.format(EXTRA_RULES=FROM_FUNCTION_EXTRA_RULES)

        message = 'Function code:\n\n' + inspect.getsource(func)

        return self._generate(prompt, message, description=description, input_schema=input_schema, output_schema=output_schema)

    def from_text(self, text: str, description: str = None, input_schema: dict = None, output_schema: dict = None) -> TaskSchema:
        """Generate a JSON schema from a textual description.

        Args:
            text (str): The description of the task.
            description (str, optional): If not None, overrides the generated description. Defaults to None.
            input_schema (dict, optional): If not None, overrides the generated input schema. Defaults to None.
            output_schema (dict, optional): If not None, overrides the generated output schema. Defaults to None.

        Returns:
            TaskSchema: The generated schema.
        """
        prompt = SCHEMA_GENERATOR_PROMPT.format(EXTRA_RULES='')

        message = 'Description of the task:\n\n' + text

        return self._generate(prompt, message, description=description, input_schema=input_schema, output_schema=output_schema)