from abc import ABC, abstractmethod
from enum import Enum
import json
from typing import Dict, List, Optional, TypeAlias

from common.errors import SchemaError
from common.function_schema import schema_from_function
from utils import compute_hash, extract_metadata

class Suitability(str, Enum):
    ADEQUATE = 'adequate'
    INADEQUATE = 'inadequate'
    PROBABLY_ADEQUATE = 'probably_adequate'
    PROBABLY_INADEQUATE = 'probably_inadequate'
    UNKNOWN = 'unknown'

class Conversation(ABC):
    @abstractmethod
    def __call__(self, message, print_output=True):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class Protocol:
    def __init__(self, protocol_document : str, sources : List[str], metadata : Optional[Dict[str, str]]):
        self.protocol_document = protocol_document
        self.sources = sources

        if metadata is None:
            try:
                metadata = extract_metadata(protocol_document)
            except:
                metadata = {}
        self.metadata = metadata

    @property
    def hash(self):
        return compute_hash(self.protocol_document)
    
    def __str__(self):
        return f'Protocol {self.hash}\nSources: {self.sources}\nMetadata: {self.metadata}\n\n{self.protocol_document}\n\n'

class TaskSchema:
    def __init__(self, description : Optional[str], input_schema : Optional[dict], output_schema : Optional[dict]):
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
    
    @staticmethod
    def from_json(json_dict : dict):
        for field in ['description', 'input', 'output']:
            if field not in json_dict:
                raise SchemaError(f'"{field}" field is required in TaskSchema')
    
        return TaskSchema(json_dict['description'], json_dict['input'], json_dict['output'])
    
    def to_json(self) -> dict:
        return {
            'description': self.description,
            'input': self.input_schema,
            'output': self.output_schema
        }
    
    @staticmethod
    def from_function(func, description : Optional[str] = None, input_schema : Optional[dict] = None, output_schema : Optional[dict] = None):
        schema = schema_from_function(func)

        if description is None:
            description = schema.get('description', None)

        if input_schema is None:
            input_schema = schema.copy()
            input_schema.pop('returns', None)
            input_schema.pop('description', None)

        if output_schema is None:
            output_schema = schema.get('returns', None)

        return TaskSchema(description, input_schema, output_schema)
    
    @staticmethod
    def from_taskschemalike(task_schema_like : 'TaskSchemaLike'):
        if isinstance(task_schema_like, TaskSchema):
            return task_schema_like
        elif isinstance(task_schema_like, dict):
            return TaskSchema.from_json(task_schema_like)
        else:
            raise SchemaError('TaskSchemaLike must be either a TaskSchema or a dict')

    def __str__(self):
        return json.dumps(self.to_json(), indent=2)

TaskSchemaLike : TypeAlias = TaskSchema | dict