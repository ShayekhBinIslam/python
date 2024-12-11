from typing import Optional

from common.core import Protocol
from common.storage import Storage, JSONStorage
from sender.components.negotiator import SenderNegotiator
from sender.policy import SimpleSenderPolicy
from sender.components.programmer import SenderProgrammer
from sender.protocol_picker import ProtocolPicker
from sender.components.querier import Querier
from sender.components.transporter import SenderTransporter, SimpleSenderTransporter
from common.executor import Executor, UnsafeExecutor

from common.core import Suitability


class SenderMemory:
    def __init__(self, storage : Storage):
        self.storage = storage

        self.storage.load_memory()

        if 'protocols' not in self.storage:
            self.storage['protocols'] = {}
        
        if 'num_conversations' not in self.storage:
            self.storage['num_conversations'] = {}
        self.storage.save_memory()
    
    def get_suitability(self, protocol_id : str, task_id : str, target : Optional[str]) -> Suitability:
        if protocol_id not in self.storage['protocols']:
            return Suitability.UNKNOWN

        if task_id not in self.storage['protocols'][protocol_id]['suitability']:
            return Suitability.UNKNOWN

        suitability = self.storage['protocols'][protocol_id]['suitability'][task_id]['default']
        if target is not None and target in self.storage['protocols'][protocol_id]['suitability'][task_id]['overrides']:
            suitability = self.storage['protocols'][protocol_id]['suitability'][task_id]['overrides'][target]

        return suitability

    def get_known_suitable_protocol_ids(self, task_id, target):
        suitable_protocols = []
        for protocol_id in self.storage['protocols'].keys():
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
        for protocol_id in self.storage['protocols'].keys():
            if self.get_suitability(protocol_id, task_id, None) == Suitability.UNKNOWN:
                unclassified_protocols.append(protocol_id)

        return unclassified_protocols
    
    def get_protocol(self, protocol_id):
        if 'protocols' not in self.storage:
            return None
        if protocol_id not in self.storage['protocols']:
            return None

        protocol_info = self.storage['protocols'][protocol_id]

        return Protocol(protocol_info['protocol'], protocol_info['sources'], protocol_info['metadata'])

    def set_default_suitability(self, protocol_id : str, task_id : str, suitability : Suitability):
        if protocol_id not in self.storage['protocols']:
            raise Exception('Protocol not in memory:', protocol_id)

        if task_id not in self.storage['protocols'][protocol_id]['suitability']:
            self.storage['protocols'][protocol_id]['suitability'][task_id] = {
                'default': Suitability.UNKNOWN,
                'overrides': {}
            }
        
        self.storage['protocols'][protocol_id]['suitability'][task_id]['default'] = suitability
        self.storage.save_memory()

    def set_suitability_override(self, protocol_id : str, task_id : str, target : str, suitability : Suitability):
        if protocol_id not in self.storage['protocols']:
            raise Exception('Protocol not in memory:', protocol_id)
        
        if task_id not in self.storage['protocols'][protocol_id]['suitability']:
            self.storage['protocols'][protocol_id]['suitability'][task_id] = {
                'default': Suitability.UNKNOWN,
                'overrides': {}
            }
        
        self.storage['protocols'][protocol_id]['suitability'][task_id]['overrides'][target] = suitability
        self.storage.save_memory()

    def register_new_protocol(self, protocol_id : str, protocol_document : str, sources : list, metadata : dict):
        if protocol_id in self.storage['protocols']:
            raise Exception('Protocol already in memory:', protocol_id)
        
        self.storage['protocols'][protocol_id] = {
            'protocol': protocol_document,
            'sources': sources,
            'metadata': metadata,
            'suitability': {}
        }
        self.storage.save_memory()


class Sender:
    def __init__(self, storage : Storage, protocol_picker : ProtocolPicker, negotiator : SenderNegotiator, programmer : SenderProgrammer, executor : Executor, querier : Querier, transporter : SenderTransporter):
        self.memory = SenderMemory(storage)
        self.protocol_picker = protocol_picker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.querier = querier
        self.transporter = transporter

    @staticmethod
    def make_default(toolformer, storage : Storage = None, protocol_picker : ProtocolPicker = None, negotiator : SenderNegotiator = None, programmer : SenderProgrammer = None, executor : Executor = None, querier : Querier = None, transporter : SenderTransporter = None):
        if storage is None:
            path = './sender_storage.json'
            storage = JSONStorage(path) # TODO
        if protocol_picker is None:
            protocol_picker = ProtocolPicker()
        if negotiator is None:
            negotiator = SenderNegotiator(toolformer)
        if programmer is None:
            programmer = SenderProgrammer(toolformer)
        if executor is None:
            executor = UnsafeExecutor()
        if querier is None:
            querier = Querier(toolformer)
        if transporter is None:
            transporter = SimpleSenderTransporter()
        
        return Sender(storage, protocol_picker, negotiator, programmer, executor, querier, transporter)

    def negotiate_protocol(self, task_schema, target) -> Optional[Protocol]:
        external_conversation = self.transporter.new_conversation(target, True, 'negotiation', None)

        def send_query(query):
            response = external_conversation(query)
            print('Response to negotiator:', response)
            return response

        protocol = self.negotiator.negotiate_protocol_for_task(task_schema, send_query)

        external_conversation.close()

        # TODO: Store the protocol document somewhere else
        if protocol is not None:
            self.memory.register_new_protocol(protocol.hash, protocol.protocol_document, protocol.sources, protocol.metadata)

        return protocol


    def execute_task(self, task_id, task_schema, task_data, target):
        # TODO: The sender components (querier, programmer, negotiator) should be aware of any tools that are available + additional info.
        
        #self.memory.increment_task_conversations(task_id, target)

        #protocol_document = self.get_protocol(task_id, task_schema, target)

        # TODO: multiround depends on the protocol
        external_conversation = self.transporter.new_conversation(target, True, None, None)

        def send_query(query):
            response = external_conversation(query)
            print('Response to sender:', response)
            return response

     
        response = self.querier(task_schema, task_data, None, send_query)
        external_conversation.close()

        return response
