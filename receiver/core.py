from typing import List

from receiver.responder import Responder
from receiver.storage import ReceiverStorage, LocalReceiverStorage
from utils import download_and_verify_protocol

from common.core import Suitability
from toolformers.base import Tool

class Receiver:
    def __init__(self, memory: ReceiverStorage, responder : Responder, protocol_checker : ReceiverProtocolChecker, tools: List[Tool]):
        self.memory = memory
        self.responder = responder
        self.protocol_checker = protocol_checker
        self.tools = tools

    def handle_query(self, protocol_hash, protocol_sources, body):
        if protocol_hash is None:
            return self.responder.reply_to_nl_query(body)
            
        if self.memory.has_implementation(protocol_hash):
            routine_path = self.memory.get_implementation_path(protocol_hash)
            return self.executor.run_routine(routine_path, body)
        else:
            self.memory.increment_conversations(protocol_hash)

        if not self.memory.has_protocol_document(protocol_hash):
            for protocol_source in protocol_sources:
                protocol_document = download_and_verify_protocol(protocol_hash, protocol_source)
                if protocol_document is not None:
                    self.memory.register_new_protocol(protocol_hash, protocol_source, protocol_document)
                    break
            else:
                return {
                    'status': 'error',
                    'message': 'No valid protocol source provided.'
                }

        if self.memory.get_suitability(protocol_hash) == Suitability.UNKNOWN:
            protocol_document = self.memory.load_protocol_document(protocol_hash)
            is_suitable = self.protocol_checker.check_protocol_for_tools(protocol_document, self.tools)
            if is_suitable:
                self.memory.set_suitability(protocol_hash, Suitability.ADEQUATE)
            else:
                self.memory.set_suitability(protocol_hash, Suitability.INADEQUATE)
            self.memory.save_memory()
        
        if self.memory.get_suitability(protocol_hash) == Suitability.ADEQUATE:
            if self.policy.should_implement_protocol(protocol_hash):
                implementation = self.programmer.write_routine_for_task(protocol_hash)
                self.memory.register_implementation(protocol_hash, implementation)
            return self.executor.execute_task(protocol_hash, body)
        else:
            return {
                'status': 'error',
                'message': 'Protocol not suitable.'
            }