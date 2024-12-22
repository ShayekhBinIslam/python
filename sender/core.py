import inspect
from typing import Optional

from common.core import Protocol
from common.storage import Storage, JSONStorage
from sender.components.negotiator import SenderNegotiator
from sender.components.programmer import SenderProgrammer
from sender.components.protocol_picker import ProtocolPicker
from sender.components.querier import Querier
from sender.components.transporter import SenderTransporter, SimpleSenderTransporter
from common.executor import Executor, RestrictedExecutor

from common.core import Suitability, TaskSchema, TaskSchemaLike
from common.memory import ProtocolMemory
from common.toolformers.base import Tool

from utils import encode_as_data_uri

class SenderMemory(ProtocolMemory):
    def __init__(self, storage : Storage):
        super().__init__(storage, num_conversations={})

    def get_suitability(self, protocol_id : str, task_id : str, target : Optional[str]) -> Suitability:
        suitability_info = super().get_extra_field(protocol_id, 'suitability', {})

        if task_id not in suitability_info:
            return Suitability.UNKNOWN
        
        if target is not None and target in suitability_info[task_id]['overrides']:
            return suitability_info[task_id]['overrides'][target]
        
        return suitability_info[task_id]['default']

    def get_known_suitable_protocol_ids(self, task_id, target):
        suitable_protocols = []
        for protocol_id in self.protocol_ids():
            if self.get_suitability(protocol_id, task_id, target) == Suitability.ADEQUATE:
                suitable_protocols.append(protocol_id)

        return suitable_protocols

    def get_suitable_protocol(self, task_id, target) -> Optional[Protocol]:
        suitable_protocols = self.get_known_suitable_protocol_ids(task_id, target)
        if len(suitable_protocols) == 0:
            return None
        return self.get_protocol(suitable_protocols[0])

    def increment_task_conversations(self, task_id, target):
        if 'num_conversations' not in self.storage:
            self.storage['num_conversations'] = {}
        if task_id not in self.storage['num_conversations']:
            self.storage['num_conversations'][task_id] = {}
        if target not in self.storage['num_conversations'][task_id]:
            self.storage['num_conversations'][task_id][target] = 0
        self.storage['num_conversations'][task_id][target] += 1

    def get_task_conversations(self, task_id, target):
        if 'num_conversations' not in self.storage:
            return 0
        if task_id not in self.storage['num_conversations']:
            return 0
        if target not in self.storage['num_conversations'][task_id]:
            return 0
        return self.storage['num_conversations'][task_id][target]
    
    def has_suitable_protocol(self, task_id, target):
        return len(self.get_known_suitable_protocol_ids(task_id, target)) > 0
    
    def get_unclassified_protocols(self, task_id):
        unclassified_protocols = []
        for protocol_id in self.protocol_ids():
            if self.get_suitability(protocol_id, task_id, None) == Suitability.UNKNOWN:
                unclassified_protocols.append(protocol_id)

        return unclassified_protocols

    def set_default_suitability(self, protocol_id : str, task_id : str, suitability : Suitability):
        suitability_info = self.get_extra_field(protocol_id, 'suitability', {})

        if task_id not in suitability_info:
            suitability_info[task_id] = {
                'default': Suitability.UNKNOWN,
                'overrides': {}
            }

        suitability_info[task_id]['default'] = suitability

        self.set_extra_field(protocol_id, 'suitability', suitability_info)

    def set_suitability_override(self, protocol_id : str, task_id : str, target : str, suitability : Suitability):
        suitability_info = self.get_extra_field(protocol_id, 'suitability', {})

        if task_id not in suitability_info:
            suitability_info[task_id] = {
                'default': Suitability.UNKNOWN,
                'overrides': {}
            }
        
        suitability_info[task_id]['overrides'][target] = suitability
        self.set_extra_field(protocol_id, 'suitability', suitability_info)

    def register_new_protocol(self, protocol_id : str, protocol_document : str, sources : list, metadata : dict):
        if protocol_id in self.storage['protocols']:
            raise Exception('Protocol already in memory:', protocol_id)
        
        super().register_new_protocol(
            protocol_id,
            protocol_document,
            sources,
            metadata,
            None,
            suitability={}
        )


class Sender:
    def __init__(
            self,
            storage : Storage,
            protocol_picker : ProtocolPicker,
            negotiator : SenderNegotiator,
            programmer : SenderProgrammer,
            executor : Executor,
            querier : Querier,
            transporter : SenderTransporter,
            protocol_threshold : int = 5,
            negotiation_threshold : int = 10,
            implementation_threshold : int = 5
        ):
        self.memory = SenderMemory(storage)
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
        storage : Storage = None,
        protocol_picker : ProtocolPicker = None,
        negotiator : SenderNegotiator = None,
        programmer : SenderProgrammer = None,
        executor : Executor = None,
        querier : Querier = None,
        transporter : SenderTransporter = None,
        protocol_threshold : int = 5,
        negotiation_threshold : int = 10,
        implementation_threshold : int = 5
    ):
        if storage is None:
            path = './sender_storage.json'
            storage = JSONStorage(path) # TODO
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
        
        return Sender(storage, protocol_picker, negotiator, programmer, executor, querier, transporter, protocol_threshold, negotiation_threshold, implementation_threshold)

    def negotiate_protocol(self, task_schema : TaskSchemaLike, target : str) -> Optional[Protocol]:
        with self.transporter.new_conversation(target, True, 'negotiation', None) as external_conversation:
            def send_query(query):
                response = external_conversation(query)
                print('Response to negotiator:', response)
                return response

            protocol = self.negotiator.negotiate_protocol_for_task(task_schema, send_query)

        # TODO: Store the protocol document somewhere else
        if protocol is not None:
            self.memory.register_new_protocol(protocol.hash, protocol.protocol_document, protocol.sources, protocol.metadata)

        return protocol

    def get_suitable_protocol(self, task_id : str, task_schema : TaskSchemaLike, target : str) -> Optional[Protocol]:
        # Look in the memory
        suitable_protocol = self.memory.get_suitable_protocol(task_id, target)

        if suitable_protocol is None and self.memory.get_task_conversations(task_id, target) > self.protocol_threshold:
            protocol_ids = self.memory.get_unclassified_protocols(task_id)
            protocols = [self.memory.get_protocol(protocol_id) for protocol_id in protocol_ids]
            suitable_protocol, protocol_evaluations = self.protocol_picker.pick_protocol(task_schema, protocols)

            for protocol_id, evaluation in protocol_evaluations.items():
                self.memory.set_default_suitability(protocol_id, task_id, evaluation)

        if suitable_protocol is None and self.memory.get_task_conversations(task_id, target) > self.negotiation_threshold:
            suitable_protocol = self.negotiate_protocol(task_schema, target)

        return suitable_protocol
    
    def get_implementation(self, protocol_id : str, task_schema):
        # Check if a routine exists and eventually create it
        implementation = self.memory.get_implementation(protocol_id)

        if implementation is None and self.memory.get_task_conversations(protocol_id, None) > self.implementation_threshold:
            protocol = self.memory.get_protocol(protocol_id)
            implementation = self.programmer(task_schema, protocol.protocol_document)
            self.memory.register_implementation(protocol_id, implementation)

        return implementation
    
    def run_routine(self, protocol_id : str, implementation : str, task_data, callback):
        def send_to_server(query : str):
            """
            Send a query to the other service based on a protocol document.

            Args:
                query (str): The query to send to the service

            Returns:
                str: The response from the service
            """

            response = callback(query)
            print('Tool run_routine responded with:', response)
            return response['body']

        send_query_tool = Tool.from_function(send_to_server) # TODO: Handle errors

        return self.executor(protocol_id, implementation, [send_query_tool], [task_data], {})

    # TODO: force_no_protocol, force_no_implementation, force_multiround
    def execute_task(self, task_id : str, task_schema : TaskSchemaLike, task_data, target : str):
        self.memory.increment_task_conversations(task_id, target)

        protocol = self.get_suitable_protocol(task_id, task_schema, target)

        # TODO: Some standardized way to support data URIs
        with self.transporter.new_conversation(
            target,
            protocol.metadata['multiround'] if protocol else True,
            protocol.hash if protocol else None,
            # Temp
            [encode_as_data_uri(protocol.protocol_document) if protocol else []]
        ) as external_conversation:
            def send_query(query):
                response = external_conversation(query)
                print('Response to sender:', response)
                return response

            implementation = None

            if protocol is not None:
                implementation = self.get_implementation(protocol.hash, task_schema)

            if implementation is None:
                response = self.querier(task_schema, task_data, protocol.protocol_document if protocol else None, send_query)
            else:
                response = self.run_routine(protocol.hash, implementation, task_data, send_query)

            return response

    def task(self, task_id : Optional[str] = None, description : Optional[str] = None, input_schema : Optional[dict] = None, output_schema : Optional[dict] = None):
        def wrapper(func):
            nonlocal task_id

            if task_id is None:
                task_id = func.__name__
            task_schema = TaskSchema.from_function(func, description=description, input_schema=input_schema, output_schema=output_schema)

            def wrapped(*args, target=None, **kwargs):
                # Figure out from the function signature what the input data should be
                signature = inspect.signature(func)
                task_data = signature.bind(*args, **kwargs)
                task_data.apply_defaults()
                task_data = task_data.arguments

                return self.execute_task(task_id, task_schema, task_data, target)

            return wrapped

        return wrapper
