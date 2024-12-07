from toolformers.base import Toolformer
from common.storage import Storage, JSONStorage
from sender.components.negotiator import SenderNegotiator
from sender.policy import SimpleSenderPolicy
from sender.components.programmer import SenderProgrammer
from sender.protocol_picker import ProtocolPicker
from sender.components.querier import Querier
from sender.components.transporter import SenderTransporter, SimpleSenderTransporter
from common.executor import Executor, UnsafeExecutor

from common.core import Suitability

from toolformers.camel import CamelToolformer
from camel.types import ModelPlatformType, ModelType
from camel.configs.openai_config import ChatGPTConfig

class SenderMemory:
    def __init__(self, storage : Storage):
        self.storage = storage
    
    def get_known_suitable_protocols(self, task_id, target):
        suitable_protocols = []
        for protocol_id, protocol_info in self.storage['protocols'].items():
            if protocol_info['task_id']['target']['suitability'] == Suitability.ADEQUATE:
                suitable_protocols.append(protocol_id)
        return suitable_protocols


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
