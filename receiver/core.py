from abc import ABC, abstractmethod
from typing import List
from common.core import Suitability, Protocol

from toolformers.base import Tool
from common.storage import Storage, JSONStorage
from common.executor import Executor, UnsafeExecutor
from receiver.components.responder import Responder
from receiver.components.protocol_checker import ReceiverProtocolChecker
from receiver.components.negotiator import ReceiverNegotiator
from receiver.components.programmer import ReceiverProgrammer

from utils import download_and_verify_protocol, extract_metadata


class ReceiverMemory:
    def __init__(self, storage : Storage):
        self.storage = storage

        self.storage.load_memory()

        if 'protocols' not in self.storage:
            self.storage['protocols'] = {}

        # TODO: Track conversations
        #if 'num_conversations' not in self.storage:
        #    self.storage['num_conversations'] = {}

        self.storage.save_memory()

    def register_new_protocol(self, protocol_id, protocol_sources, protocol_document, metadata):
        self.storage['protocols'][protocol_id] = {
            'sources': protocol_sources,
            'protocol': protocol_document, # TODO: Rename to 'document'?
            'metadata': metadata,
            'suitability' : Suitability.UNKNOWN,
            'implementation' : None
        }
        self.storage.save_memory()

    def get_protocol(self, protocol_id : str):
        if protocol_id not in self.storage['protocols']:
            return None

        protocol_info = self.storage['protocols'][protocol_id]
        return Protocol(protocol_info['protocol'], protocol_info['sources'], protocol_info['metadata'])
    
    def set_suitability(self, protocol_id : str, suitability : Suitability):
        self.storage['protocols'][protocol_id]['suitability'] = suitability
        self.storage.save_memory()
    
    def is_unknown(self, protocol_id : str):
        return protocol_id not in self.storage['protocols']
    
    def is_adequate(self, protocol_id : str):
        return self.storage['protocols'][protocol_id]['suitability'] == Suitability.ADEQUATE
    
    def get_implementation(self, protocol_id : str):
        # TODO: Should the implementation be included in Protocol?
        if protocol_id not in self.storage['protocols']:
            return None
        return self.storage['protocols'][protocol_id]['implementation']
    
    def register_implementation(self, protocol_id, implementation):
        if protocol_id not in self.storage['protocols']:
            raise Exception('Protocol not in memory:', protocol_id)

        self.storage['protocols'][protocol_id]['implementation'] = implementation
        self.storage.save_memory()

class Receiver:
    def __init__(self, storage : Storage, responder : Responder, protocol_checker : ReceiverProtocolChecker, negotiator : ReceiverNegotiator, programmer : ReceiverProgrammer, executor: Executor, tools: List[Tool], additional_info : str = ''):
        self.memory = ReceiverMemory(storage)
        self.responder = responder
        self.protocol_checker = protocol_checker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.tools = tools
        self.additional_info = additional_info

    @staticmethod
    def make_default(toolformer, storage : Storage = None, responder : Responder = None, protocol_checker : ReceiverProtocolChecker = None, negotiator: ReceiverNegotiator = None, programmer : ReceiverProgrammer = None, executor : Executor = None, tools : List[Tool] = None, additional_info : str = ''):
        if tools is None:
            tools = []

        if storage is None:
            path = './receiver_storage.json'
            storage = JSONStorage(path) # TODO

        if responder is None:
            responder = Responder(toolformer)

        if protocol_checker is None:
            protocol_checker = ReceiverProtocolChecker(toolformer)

        if negotiator is None:
            negotiator = ReceiverNegotiator(toolformer)
        
        if programmer is None:
            programmer = ReceiverProgrammer(toolformer)

        if executor is None:
            executor = UnsafeExecutor() # TODO: UnsafeExecutor cannot be the default

        return Receiver(storage, responder, protocol_checker, negotiator, programmer, executor, tools, additional_info)
    
    def get_implementation(self, protocol_id : str):
        # Check if a routine exists and eventually create it
        implementation = self.memory.get_implementation(protocol_id)

        if implementation is None: # TODO: Decide when to implement # and self.memory.get_task_conversations(protocol_id, None) > -1:
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
            if self.memory.is_unknown(protocol_hash):
                for protocol_source in protocol_sources:
                    protocol_document = download_and_verify_protocol(protocol_hash, protocol_source)
                    if protocol_document is not None:
                        break

                if protocol_document is None:
                    raise Exception('Failed to download protocol')
                
                metadata = extract_metadata(protocol_document)
                self.memory.register_new_protocol(protocol_hash, protocol_sources, protocol_document, metadata)

                if self.protocol_checker(protocol_document, self.tools):
                    self.memory.set_suitability(protocol_hash, Suitability.ADEQUATE)
                else:
                    self.memory.set_suitability(protocol_hash, Suitability.INADEQUATE)
            else:
                metadata = self.memory.get_protocol(protocol_hash).metadata

            if self.memory.is_adequate(protocol_hash):
                protocol_document = self.memory.get_protocol(protocol_hash).protocol_document
            else:
                raise Exception('Unsuitable protocol')

            implementation = self.get_implementation(protocol_hash)

        if implementation is None:
            return self.responder.create_conversation(protocol_document, self.tools, self.additional_info)
        else:
            return self.executor.new_conversation(protocol_hash, implementation, metadata.get('multiround', False), self.tools)