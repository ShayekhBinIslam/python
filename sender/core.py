from toolformers.base import Toolformer
from common.storage import Storage, JSONStorage
from sender.components.negotiator import SenderNegotiator
from sender.policy import SimpleSenderPolicy
from sender.components.programmer import SenderProgrammer
from sender.protocol_picker import ProtocolPicker
from sender.components.querier import Querier
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
    def __init__(self, storage : Storage = None, protocol_picker : ProtocolPicker = None, negotiator : SenderNegotiator = None, programmer : SenderProgrammer = None, executor : Executor = None, querier : Querier = None, toolformer: Toolformer = None):
        if toolformer is None:
            toolformer = CamelToolformer(ModelPlatformType.OPENAI, ModelType.GPT_4O, {})
        
        if storage is None:
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
            transporter = SenderTransporter() # TODO

        self.storage = storage
        self.protocol_picker = protocol_picker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.querier = querier
        self.transporter = transporter
        #self.toolformer = toolformer

    def execute_task(self, task_id, task_schema, task_data, target):
        
        self.transporter.send()
