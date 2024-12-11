from abc import ABC, abstractmethod
from typing import List

from toolformers.base import Tool
from common.storage import Storage, JSONStorage
from receiver.components.responder import Responder
from receiver.components.protocol_checker import ReceiverProtocolChecker
from receiver.components.negotiator import ReceiverNegotiator


class Receiver:
    def __init__(self, storage : Storage, responder : Responder, protocol_checker : ReceiverProtocolChecker, negotiator : ReceiverNegotiator, tools: List[Tool], additional_info : str = ''):
        self.storage = storage
        self.responder = responder
        self.protocol_checker = protocol_checker
        self.negotiator = negotiator
        self.tools = tools
        self.additional_info = additional_info

    @staticmethod
    def make_default(toolformer, storage : Storage = None, responder : Responder = None, protocol_checker : ReceiverProtocolChecker = None, negotiator: ReceiverNegotiator = None, tools : List[Tool] = None, additional_info : str = ''):
        if tools is None:
            tools = []

        if storage is None:
            path = './receiver_storage.json'
            storage = JSONStorage(path) # TODO

        if responder is None:
            responder = Responder(toolformer)

        if protocol_checker is None:
            protocol_checker = ReceiverProtocolChecker()

        if negotiator is None:
            negotiator = ReceiverNegotiator(toolformer)

        return Receiver(storage, responder, protocol_checker, negotiator, tools, additional_info)

    def create_conversation(self, protocol_hash, protocol_sources):
        if protocol_hash == 'negotiation':
            return self.negotiator.create_conversation(self.tools, self.additional_info)

        return self.responder.create_conversation(None, self.tools, self.additional_info)