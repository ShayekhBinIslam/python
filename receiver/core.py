from typing import List
from common.core import Suitability

from common.toolformers.base import ToolLike
from common.memory import ProtocolMemory
from common.storage import Storage, JSONStorage
from common.executor import Executor, RestrictedExecutor
from receiver.components.responder import Responder
from receiver.components.protocol_checker import ReceiverProtocolChecker
from receiver.components.negotiator import ReceiverNegotiator
from receiver.components.programmer import ReceiverProgrammer

from utils import download_and_verify_protocol, extract_metadata


class ReceiverMemory(ProtocolMemory):
    def register_new_protocol(self, protocol_id, protocol_sources, protocol_document, metadata):
        super().register_new_protocol(
            protocol_id,
            protocol_document,
            protocol_sources,
            metadata,
            None,
            suitability=Suitability.UNKNOWN,
            conversations=0
        )
    
    def get_protocol_conversations(self, protocol_id):
        return self.get_extra_field(protocol_id, 'conversations', 0)
    
    def increment_protocol_conversations(self, protocol_id):
        self.set_extra_field(protocol_id, 'conversations', self.get_protocol_conversations(protocol_id) + 1)

    def set_suitability(self, protocol_id : str, suitability : Suitability):
        super().set_extra_field(protocol_id, 'suitability', suitability)

    def get_suitability(self, protocol_id : str) -> Suitability:
        return self.get_extra_field(protocol_id, 'suitability', Suitability.UNKNOWN)

class Receiver:
    def __init__(self, storage : Storage, responder : Responder, protocol_checker : ReceiverProtocolChecker, negotiator : ReceiverNegotiator, programmer : ReceiverProgrammer, executor: Executor, tools: List[ToolLike], additional_info : str = '', implementation_threshold : int = 5):
        self.memory = ReceiverMemory(storage)
        self.responder = responder
        self.protocol_checker = protocol_checker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.tools = tools
        self.additional_info = additional_info
        self.implementation_threshold = implementation_threshold

    @staticmethod
    def make_default(toolformer, storage : Storage = None, responder : Responder = None, protocol_checker : ReceiverProtocolChecker = None, negotiator: ReceiverNegotiator = None, programmer : ReceiverProgrammer = None, executor : Executor = None, tools : List[ToolLike] = None, additional_info : str = '', storage_path : str = './receiver_storage.json', implementation_threshold : int = 5):
        if tools is None:
            tools = []

        if storage is None:
            storage = JSONStorage(storage_path)

        if responder is None:
            responder = Responder(toolformer)

        if protocol_checker is None:
            protocol_checker = ReceiverProtocolChecker(toolformer)

        if negotiator is None:
            negotiator = ReceiverNegotiator(toolformer)
        
        if programmer is None:
            programmer = ReceiverProgrammer(toolformer)

        if executor is None:
            executor = RestrictedExecutor()

        return Receiver(storage, responder, protocol_checker, negotiator, programmer, executor, tools, additional_info, implementation_threshold)
    
    def get_implementation(self, protocol_id : str):
        # Check if a routine exists and eventually create it
        implementation = self.memory.get_implementation(protocol_id)

        if implementation is None and self.memory.get_protocol_conversations(protocol_id) >= self.implementation_threshold:
            protocol = self.memory.get_protocol(protocol_id)
            implementation = self.programmer(self.tools, protocol.protocol_document, protocol.metadata.get('multiround', False))
            self.memory.register_implementation(protocol_id, implementation)

        return implementation

    def create_conversation(self, protocol_hash, protocol_sources):
        if protocol_hash == 'negotiation':
            return self.negotiator.create_conversation(self.tools, self.additional_info)

        protocol_document = None
        implementation = None

        if protocol_hash is not None:
            self.memory.increment_protocol_conversations(protocol_hash)

            if not self.memory.is_known(protocol_hash):
                for protocol_source in protocol_sources:
                    protocol_document = download_and_verify_protocol(protocol_hash, protocol_source)
                    if protocol_document is not None:
                        break

                if protocol_document is None:
                    raise Exception('Failed to download protocol')
                
                metadata = extract_metadata(protocol_document)
                self.memory.register_new_protocol(protocol_hash, protocol_sources, protocol_document, metadata)

            protocol = self.memory.get_protocol(protocol_hash)
            protocol_document = protocol.protocol_document
            metadata = protocol.metadata

            if self.memory.get_suitability(protocol_hash) == Suitability.UNKNOWN:
                if self.protocol_checker(protocol_document, self.tools):
                    self.memory.set_suitability(protocol_hash, Suitability.ADEQUATE)
                else:
                    self.memory.set_suitability(protocol_hash, Suitability.INADEQUATE)

            if self.memory.get_suitability(protocol_hash) == Suitability.ADEQUATE:
                protocol_document = self.memory.get_protocol(protocol_hash).protocol_document
            else:
                raise Exception('Unsuitable protocol')

            implementation = self.get_implementation(protocol_hash)

        if implementation is None:
            return self.responder.create_conversation(protocol_document, self.tools, self.additional_info)
        else:
            return self.executor.new_conversation(protocol_hash, implementation, metadata.get('multiround', False), self.tools)