from abc import ABC, abstractmethod
from typing import List

from toolformers.base import Tool
from common.storage import Storage, JSONStorage
from receiver.components.responder import Responder
from receiver.components.protocol_checker import ReceiverProtocolChecker


class Receiver:
    def __init__(self, storage : Storage, responder : Responder, protocol_checker : ReceiverProtocolChecker, tools: List[Tool], additional_info : str = ''):
        self.storage = storage
        self.responder = responder
        self.protocol_checker = protocol_checker
        self.tools = tools
        self.additional_info = additional_info

    @staticmethod
    def make_default(toolformer, storage : Storage = None, responder : Responder = None, protocol_checker : ReceiverProtocolChecker = None, tools : List[Tool] = None, additional_info : str = ''):
        if tools is None:
            tools = []

        if storage is None:
            path = './receiver_storage.json'
            storage = JSONStorage(path) # TODO

        if responder is None:
            responder = Responder(toolformer, tools, additional_info)

        if protocol_checker is None:
            protocol_checker = ReceiverProtocolChecker()

        return Receiver(storage, responder, protocol_checker, tools, additional_info)

    def create_conversation(self, protocol_hash, protocol_sources):
        return self.responder.create_conversation(None)