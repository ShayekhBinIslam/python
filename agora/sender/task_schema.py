from collections.abc import Mapping
import json
from typing import Callable, Optional, TypeAlias, TYPE_CHECKING

from agora.common.errors import SchemaError
from agora.common.function_schema import schema_from_function

if TYPE_CHECKING:
    from agora.sender.schema_generator import TaskSchemaGenerator

class TaskSchema(Mapping):
    """Defines the schema for a task, including description and input/output schemas."""

    def __init__(
        self,
        description: Optional[str],
        input_schema: Optional[dict],
        output_schema: Optional[dict]
    ):
        """Initializes the TaskSchema.

        Args:
            description (Optional[str]): A description of the task.
            input_schema (Optional[dict]): The JSON schema of the input data.
            output_schema (Optional[dict]): The JSON schema of the output data.
        """
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
    
    @property
    def fields(self) -> dict:
        return {
            'description': self.description,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema
        }
    
    def __len__(self):
        return len(self.fields)
    
    def __iter__(self):
        return iter(self.fields)
    
    def __getitem__(self, key):
        return self.fields[key]

    @staticmethod
    def from_json(json_dict : dict) -> 'TaskSchema':
        """
        Creates a TaskSchema from a JSON dictionary.

        Args:
            json_dict (dict): The JSON dictionary containing task schema details.

        Returns:
            TaskSchema: An instance of TaskSchema based on the provided JSON.
        
        Raises:
            SchemaError: If required fields are missing in the JSON dictionary.
        """
        for field in ['description', 'input_schema', 'output_schema']:
            if field not in json_dict:
                raise SchemaError(f'"{field}" field is required in TaskSchema')
    
        return TaskSchema(json_dict['description'], json_dict['input_schema'], json_dict['output_schema'])
    
    def to_json(self) -> dict:
        """
        Converts the TaskSchema to a JSON dictionary.

        Returns:
            dict: The JSON representation of the TaskSchema.
        """
        return self.fields
    
    @staticmethod
    def from_function(
        func: Callable,
        description: Optional[str] = None,
        input_schema: Optional[dict] = None,
        output_schema: Optional[dict] = None,
        generator: Optional['TaskSchemaGenerator'] = None
    ) -> 'TaskSchema':
        """
        Creates a TaskSchema from a function, inferring schemas if necessary.

        Args:
            func (Callable): The function to infer the schema from.
            description (Optional[str], optional): Overrides the task description. Defaults to None.
            input_schema (Optional[dict], optional): Overrides the input schema. Defaults to None.
            output_schema (Optional[dict], optional): Overrides the output schema. Defaults to None.
            generator (Optional[TaskSchemaGenerator], optional): Used to fill the fields that could not be parsed from function introspection. Defaults to None.

        Returns:
            TaskSchema: An instance of TaskSchema based on the function.
        """

        if description is not None and input_schema is None and output_schema is None:
            # We can generate the schema directly
            return TaskSchema(description, input_schema, output_schema)

        try:
            schema = schema_from_function(func)
        except Exception as e:
            if generator is None:
                raise e
            schema = generator.from_function(func, description, input_schema, output_schema).fields

        if description is None:
            description = schema.get('description', None)

        if input_schema is None:
            input_schema = schema.get('input_schema', None)

        if output_schema is None:
            output_schema = schema.get('output_schema', None)

        # TODO: Throw an error if any of the fields are still None

        return TaskSchema(description, input_schema, output_schema)
    
    @staticmethod
    def from_taskschemalike(task_schema_like : 'TaskSchemaLike') -> 'TaskSchema':
        """
        Converts a TaskSchema-like object into a TaskSchema instance.

        Args:
            task_schema_like (TaskSchemaLike): The TaskSchema-like object to convert.

        Returns:
            TaskSchema: An instance of TaskSchema.
        
        Raises:
            SchemaError: If the input is neither a TaskSchema nor a dictionary.
        """
        if isinstance(task_schema_like, TaskSchema):
            return task_schema_like
        elif isinstance(task_schema_like, dict):
            return TaskSchema.from_json(task_schema_like)
        else:
            raise SchemaError('TaskSchemaLike must be either a TaskSchema or a dict')

    def __str__(self) -> str:
        """
        Returns the JSON string representation of the TaskSchema.

        Returns:
            str: The JSON-formatted string of the TaskSchema.
        """
        return json.dumps(self.to_json(), indent=2)

TaskSchemaLike : TypeAlias = TaskSchema | dict