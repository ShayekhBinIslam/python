import inspect
from typing import Any, Optional

from agora.common.core import Protocol, Suitability, TaskSchema, TaskSchemaLike
from agora.common.errors import ExecutionError, StorageError
from agora.common.storage import Storage, JSONStorage
from agora.sender.components.negotiator import SenderNegotiator
from agora.sender.components.programmer import SenderProgrammer
from agora.sender.components.protocol_picker import ProtocolPicker
from agora.sender.components.querier import Querier
from agora.sender.components.transporter import SenderTransporter, SimpleSenderTransporter
from agora.common.executor import Executor, RestrictedExecutor

from agora.common.memory import ProtocolMemory
from agora.common.toolformers.base import Tool

from agora.sender.schema_generator import SchemaGenerator

from agora.utils import encode_as_data_uri

class SenderMemory(ProtocolMemory):
    """
    Manages the memory for the Sender, including protocol suitability and task conversations.
    """

    def __init__(self, storage: Storage):
        """
        Initializes SenderMemory with a storage backend.

        Args:
            storage (Storage): The storage backend for memory.
        """
        super().__init__(storage, num_conversations={})

    def get_suitability(self, protocol_id: str, task_id: str, target: Optional[str]) -> Suitability:
        """
        Retrieves the suitability status for a given protocol ID and task ID.

        Args:
            protocol_id (str): The protocol identifier.
            task_id (str): The task identifier.
            target (Optional[str]): The target system or service.

        Returns:
            Suitability: The stored suitability status.
        """
        suitability_info = super().get_extra_field(protocol_id, 'suitability', {})

        if task_id not in suitability_info:
            return Suitability.UNKNOWN
        
        if target is not None and target in suitability_info[task_id]['overrides']:
            return suitability_info[task_id]['overrides'][target]
        
        return suitability_info[task_id]['default']

    def get_known_suitable_protocol_ids(self, task_id, target):
        """
        Returns known suitable protocol IDs for the given task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            list: A list of known suitable protocol IDs.
        """
        suitable_protocols = []
        for protocol_id in self.protocol_ids():
            if self.get_suitability(protocol_id, task_id, target) == Suitability.ADEQUATE:
                suitable_protocols.append(protocol_id)

        return suitable_protocols

    def get_suitable_protocol(self, task_id, target) -> Optional[Protocol]:
        """
        Retrieves a suitable protocol object for the given task and target if available.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            Optional[Protocol]: The first suitable protocol found or None if none available.
        """
        suitable_protocols = self.get_known_suitable_protocol_ids(task_id, target)
        if len(suitable_protocols) == 0:
            return None
        return self.get_protocol(suitable_protocols[0])

    def increment_task_conversations(self, task_id, target):
        """
        Increments the conversation counter for a given task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.
        """
        if 'num_conversations' not in self.storage:
            self.storage['num_conversations'] = {}
        if task_id not in self.storage['num_conversations']:
            self.storage['num_conversations'][task_id] = {}
        if target not in self.storage['num_conversations'][task_id]:
            self.storage['num_conversations'][task_id][target] = 0
        self.storage['num_conversations'][task_id][target] += 1

    def get_task_conversations(self, task_id, target):
        """
        Retrieves the number of stored conversations for a task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            int: The number of conversations.
        """
        if 'num_conversations' not in self.storage:
            return 0
        if task_id not in self.storage['num_conversations']:
            return 0
        if target not in self.storage['num_conversations'][task_id]:
            return 0
        return self.storage['num_conversations'][task_id][target]
    
    def has_suitable_protocol(self, task_id, target):
        """
        Checks whether a suitable protocol exists for a given task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            bool: True if a suitable protocol exists, otherwise False.
        """
        return len(self.get_known_suitable_protocol_ids(task_id, target)) > 0
    
    def get_unclassified_protocols(self, task_id):
        """Get protocols that have not been classified for a specific task.

        Args:
            task_id: The identifier of the task.

        Returns:
            List[str]: A list of unclassified protocol IDs.
        """
        unclassified_protocols = []
        for protocol_id in self.protocol_ids():
            if self.get_suitability(protocol_id, task_id, None) == Suitability.UNKNOWN:
                unclassified_protocols.append(protocol_id)

        return unclassified_protocols

    def set_default_suitability(self, protocol_id: str, task_id: str, suitability: Suitability):
        """Set the default suitability for a protocol and task.

        Args:
            protocol_id (str): The identifier of the protocol.
            task_id (str): The identifier of the task.
            suitability (Suitability): The default suitability status to set.
        """
        suitability_info = self.get_extra_field(protocol_id, 'suitability', {})

        if task_id not in suitability_info:
            suitability_info[task_id] = {
                'default': Suitability.UNKNOWN,
                'overrides': {}
            }

        suitability_info[task_id]['default'] = suitability

        self.set_extra_field(protocol_id, 'suitability', suitability_info)

    def set_suitability_override(self, protocol_id: str, task_id: str, target: str, suitability: Suitability):
        """Override the suitability of a protocol for a specific task and target.

        Args:
            protocol_id (str): The identifier of the protocol.
            task_id (str): The identifier of the task.
            target (str): The target for which the suitability is overridden.
            suitability (Suitability): The overridden suitability status.
        """
        suitability_info = self.get_extra_field(protocol_id, 'suitability', {})

        if task_id not in suitability_info:
            suitability_info[task_id] = {
                'default': Suitability.UNKNOWN,
                'overrides': {}
            }
        
        suitability_info[task_id]['overrides'][target] = suitability
        self.set_extra_field(protocol_id, 'suitability', suitability_info)

    def register_new_protocol(self, protocol_id: str, protocol_document: str, sources: list, metadata: dict):
        """Register a new protocol with the given sources, document, and metadata.

        Args:
            protocol_id (str): The identifier of the new protocol.
            protocol_document (str): The document describing the protocol.
            sources (list): A list of sources where the protocol is referenced.
            metadata (dict): Additional metadata related to the protocol.
        """
        if protocol_id in self.storage['protocols']:
            raise StorageError('Protocol already in memory:', protocol_id)
        
        super().register_new_protocol(
            protocol_id,
            protocol_document,
            sources,
            metadata,
            None,
            suitability={}
        )


class Sender:
    """
    Main Sender class responsible for orchestrating protocols, components, and memory.
    """

    def __init__(
            self,
            memory: SenderMemory,
            protocol_picker: ProtocolPicker,
            negotiator: SenderNegotiator,
            programmer: SenderProgrammer,
            executor: Executor,
            querier: Querier,
            transporter: SenderTransporter,
            protocol_threshold: int = 5,
            negotiation_threshold: int = 10,
            implementation_threshold: int = 5
        ):
        """Initialize the Sender with the necessary components and thresholds.

        Args:
            memory (SenderMemory): Memory component for storing protocols and task conversations.
            protocol_picker (ProtocolPicker): Component responsible for selecting protocols.
            negotiator (SenderNegotiator): Handles negotiation of protocols.
            programmer (SenderProgrammer): Generates protocol implementations.
            executor (Executor): Executes protocol implementations.
            querier (Querier): Manages querying external services.
            transporter (SenderTransporter): Handles the transportation of messages.
            protocol_threshold (int, optional): Threshold for protocol selection. Defaults to 5.
            negotiation_threshold (int, optional): Threshold for negotiation attempts. Defaults to 10.
            implementation_threshold (int, optional): Threshold for implementation generation. Defaults to 5.
        """
        self.memory = memory
        self.protocol_picker = protocol_picker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.querier = querier
        self.transporter = transporter
        self.protocol_threshold = protocol_threshold
        self.negotiation_threshold = negotiation_threshold
        self.implementation_threshold = implementation_threshold

    @staticmethod
    def make_default(
        toolformer,
        storage: Storage = None,
        protocol_picker: ProtocolPicker = None,
        negotiator: SenderNegotiator = None,
        programmer: SenderProgrammer = None,
        executor: Executor = None,
        querier: Querier = None,
        transporter: SenderTransporter = None,
        storage_path: str = './agora/storage/sender.json',
        protocol_threshold: int = 5,
        negotiation_threshold: int = 10,
        implementation_threshold: int = 5
    ):
        """Create a default Sender instance with optional custom components.

        Args:
            toolformer: The toolformer instance to use for creating components.
            storage (Storage, optional): Custom storage backend. Defaults to None.
            protocol_picker (ProtocolPicker, optional): Custom protocol picker. Defaults to None.
            negotiator (SenderNegotiator, optional): Custom negotiator. Defaults to None.
            programmer (SenderProgrammer, optional): Custom programmer. Defaults to None.
            executor (Executor, optional): Custom executor. Defaults to None.
            querier (Querier, optional): Custom querier. Defaults to None.
            transporter (SenderTransporter, optional): Custom transporter. Defaults to None.
            storage_path (str, optional): Path to the storage file. Defaults to './sender_storage.json'.
            protocol_threshold (int, optional): Threshold for protocol selection. Defaults to 5.
            negotiation_threshold (int, optional): Threshold for negotiation attempts. Defaults to 10.
            implementation_threshold (int, optional): Threshold for implementation generation. Defaults to 5.

        Returns:
            Sender: A configured Sender instance.
        """
        if storage is None:
            storage = JSONStorage(storage_path)
        memory = SenderMemory(storage)

        if protocol_picker is None:
            protocol_picker = ProtocolPicker(toolformer)
        if negotiator is None:
            negotiator = SenderNegotiator(toolformer)
        if programmer is None:
            programmer = SenderProgrammer(toolformer)
        if executor is None:
            executor = RestrictedExecutor()
        if querier is None:
            querier = Querier(toolformer)
        if transporter is None:
            transporter = SimpleSenderTransporter()
        
        return Sender(memory, protocol_picker, negotiator, programmer, executor, querier, transporter, protocol_threshold, negotiation_threshold, implementation_threshold)

    def _negotiate_protocol(self, task_schema: TaskSchemaLike, target: str) -> Optional[Protocol]:
        """Negotiate a protocol based on the task schema and target.

        Args:
            task_schema (TaskSchemaLike): The schema of the task to be performed.
            target (str): The target for which the protocol is being negotiated.

        Returns:
            Optional[Protocol]: The negotiated Protocol object if successful, else None.
        """
        with self.transporter.new_conversation(target, True, 'negotiation', None) as external_conversation:
            def send_query(query):
                response = external_conversation(query)
                # print('Response to negotiator:', response)
                return response

            protocol = self.negotiator(task_schema, send_query)

        if protocol is not None:
            self.memory.register_new_protocol(protocol.hash, protocol.protocol_document, protocol.sources, protocol.metadata)

        return protocol

    def _get_suitable_protocol(self, task_id: str, task_schema: TaskSchemaLike, target: str) -> Optional[Protocol]:
        """Retrieve a suitable protocol for the given task and target.

        Args:
            task_id (str): The identifier of the task.
            task_schema (TaskSchemaLike): The schema of the task to be performed.
            target (str): The target for which a suitable protocol is needed.

        Returns:
            Optional[Protocol]: A suitable Protocol object if found, else None.
        """
        # Look in the memory
        suitable_protocol = self.memory.get_suitable_protocol(task_id, target)

        if suitable_protocol is None and self.memory.get_task_conversations(task_id, target) > self.protocol_threshold:
            protocol_ids = self.memory.get_unclassified_protocols(task_id)
            protocols = [self.memory.get_protocol(protocol_id) for protocol_id in protocol_ids]
            suitable_protocol, protocol_evaluations = self.protocol_picker.pick_protocol(task_schema, protocols)

            for protocol_id, evaluation in protocol_evaluations.items():
                self.memory.set_default_suitability(protocol_id, task_id, evaluation)

        if suitable_protocol is None and self.memory.get_task_conversations(task_id, target) > self.negotiation_threshold:
            suitable_protocol = self._negotiate_protocol(task_schema, target)

        return suitable_protocol
    
    def _get_implementation(self, protocol_id: str, task_schema):
        """Obtain the implementation for a specific protocol and task schema.

        Args:
            protocol_id (str): The identifier of the protocol.
            task_schema: The schema of the task to be performed.

        Returns:
            str: The implementation code for the protocol.
        """
        # Check if a routine exists and eventually create it
        implementation = self.memory.get_implementation(protocol_id)

        if implementation is None and self.memory.get_task_conversations(protocol_id, None) > self.implementation_threshold:
            protocol = self.memory.get_protocol(protocol_id)
            implementation = self.programmer(task_schema, protocol.protocol_document)
            self.memory.register_implementation(protocol_id, implementation)

        return implementation
    
    def _run_routine(self, protocol_id: str, implementation: str, task_data, callback):
        """Run the routine associated with a protocol using the provided implementation and task data.

        Args:
            protocol_id (str): The identifier of the protocol.
            implementation (str): The implementation code to execute.
            task_data: The data required for the task.
            callback: The callback function to send queries to the external service.

        Returns:
            Any: The result of the routine execution.
        """
        def send_to_server(query: str):
            """Send a query to the other service based on a protocol document.

            Args:
                query (str): The query to send to the service

            Returns:
                str: The response from the service
            """

            response = callback(query)
            # print('Tool run_routine responded with:', response)
            return response['body']

        send_query_tool = Tool.from_function(send_to_server) # TODO: Handle errors

        return self.executor(protocol_id, implementation, [send_query_tool], [task_data], {})

    def execute_task(
            self,
            task_id: str,
            task_schema: TaskSchemaLike,
            task_data, target: str,
            force_no_protocol: bool = False,
            force_llm: bool = False,
        ) -> Any:
        """Execute a task by selecting and running an appropriate protocol or falling back to querying.

        Args:
            task_id (str): The identifier of the task.
            task_schema (TaskSchemaLike): The schema of the task to be performed.
            task_data: The data required for the task.
            target (str): The target for which the task is being executed.
            force_no_protocol (bool, optional): If True, forces execution without a protocol. Defaults to False.
            force_llm (bool, optional): If True, forces execution using a language model. Defaults to False.

        Returns:
            Any: The result of the task execution.
        """
        self.memory.increment_task_conversations(task_id, target)

        if force_no_protocol:
            protocol = None
        else:
            protocol = self._get_suitable_protocol(task_id, task_schema, target)

        sources = []

        if protocol is not None:
            sources = protocol.sources

            if len(sources) == 0:
                # If there are no sources, use a data URI as source
                sources = [encode_as_data_uri(protocol.protocol_document)]

        with self.transporter.new_conversation(
            target,
            protocol.metadata['multiround'] if protocol else True,
            protocol.hash if protocol else None,
            sources
        ) as external_conversation:
            def send_query(query):
                response = external_conversation(query)
                # print('Response to sender:', response)
                return response

            implementation = None

            if protocol is not None and not force_llm:
                implementation = self._get_implementation(protocol.hash, task_schema)

            if implementation is None:
                response = self.querier(task_schema, task_data, protocol.protocol_document if protocol else None, send_query)
            else:
                try:
                    response = self._run_routine(protocol.hash, implementation, task_data, send_query)
                except ExecutionError as e:
                    # print('Error running routine:', e)
                    # print('Fallback to querier')

                    response = self.querier(task_schema, task_data, protocol.protocol_document if protocol else None, send_query)

            return response

    def task(self, task_id: Optional[str] = None, description: Optional[str] = None, input_schema: Optional[dict] = None, output_schema: Optional[dict] = None, schema_generator: Optional[SchemaGenerator] = None):
        """Decorator to define a task with optional schemas and description.

        Args:
            task_id (str, optional): The identifier of the task. Defaults to None.
            description (str, optional): A brief description of the task. Defaults to None.
            input_schema (dict, optional): The input schema for the task. Defaults to None.
            output_schema (dict, optional): The output schema for the task. Defaults to None.

        Returns:
            Callable: The decorated function.
        """
        def wrapper(func):
            nonlocal task_id

            if task_id is None:
                task_id = func.__name__
            
            try:
                task_schema = TaskSchema.from_function(func, description=description, input_schema=input_schema, output_schema=output_schema)
            except Exception as e:
                if schema_generator is None:
                    raise e

                task_schema = schema_generator.from_function(func)

            def wrapped(*args, target=None, **kwargs):
                # Figure out from the function signature what the input data should be
                signature = inspect.signature(func)
                task_data = signature.bind(*args, **kwargs)
                task_data.apply_defaults()
                task_data = task_data.arguments

                return self.execute_task(task_id, task_schema, task_data, target)

            if 'target' in task_schema.input_schema['required']:
                raise ValueError('The task schema should not require a target field')

            tool_input_schema = dict(task_schema.input_schema)
            tool_input_schema['properties']['target'] = {
                'type': 'string',
                'description': 'The URL of the target system or service for the task'
            }

            tool = Tool(wrapped.__name__, task_schema.description, tool_input_schema, task_schema.output_schema, wrapped)

            return tool.as_annotated_function()

        return wrapper
