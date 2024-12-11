# The responder is a special toolformer that replies to a service based on a protocol document.
# It receives the protocol document and writes the response that must be sent to the system.

import json
import os
from pathlib import Path

from toolformers.base import Toolformer

from toolformers.base import Conversation
from common.storage import Storage

# TODO: A tool to declare an error?


PROTOCOL_RESPONDER_PROMPT = 'You are ResponderGPT. Below you will find a document describing detailing how to respond to a query. '\
    'The communication might involve multiple rounds of back-and-forth.' \
    'Use the provided functions to execute what is requested and provide the response according to the protocol\'s specification. ' \
    'Only reply with the response itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.'# \
   # 'If you do not have enough information to reply, or if you cannot execute the request, reply with "ERROR" (without quotes).'

NL_RESPONDER_PROMPT = 'You are NaturalLanguageResponderGPT. You will receive a query from a user. ' \
    'Use the provided functions to execute what is requested and reply with a response (in natural language). ' \
    'Important: the user does not have the capacity to respond to follow-up questions, so if you think you have enough information to reply/execute the actions, do so.'
    #'If you do not have enough information to reply, if you cannot execute the request, or if the request is invalid, reply with "ERROR" (without quotes).' \

class Responder:
    def __init__(self, toolformer : Toolformer):
        self.toolformer = toolformer

    def create_protocol_conversation(self, protocol_document, tools, additional_info : str):
        print('===NL RESPONDER (WITH PROTOCOL)===')

        prompt = PROTOCOL_RESPONDER_PROMPT + additional_info + '\n\nThe protocol is the following:\n\n' + protocol_document

        return self.toolformer.new_conversation(prompt, tools, category='conversation')


    def create_nl_conversation(self, tools, additional_info : str):
        print('===NL RESPONDER (NO PROTOCOL)===')
        print(NL_RESPONDER_PROMPT + additional_info)

        print('Preparing NL response with tools:', [tool.name for tool in tools])

        conversation = self.toolformer.new_conversation(NL_RESPONDER_PROMPT + additional_info, tools, category='conversation')
        return conversation

    def create_conversation(self, protocol_document, tools, additional_info : str):
        if protocol_document is None:
            return self.create_nl_conversation(tools, additional_info)
        else:
            return self.create_protocol_conversation(protocol_document, tools, additional_info)