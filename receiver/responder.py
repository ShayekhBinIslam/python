# The responder is a special toolformer that replies to a service based on a protocol document.
# It receives the protocol document and writes the response that must be sent to the system.

import json
import os
from pathlib import Path

from toolformers.base import Toolformer

from common.storage import Storage

# TODO: A tool to declare an error?


PROTOCOL_RESPONDER_PROMPT = 'You are ResponderGPT. You will receive a protocol document detailing how to respond to a query. '\
    'Use the provided functions to execute what is requested and provide the response according to the protocol\'s specification. ' \
    'Only reply with the response itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.'# \
   # 'If you do not have enough information to reply, or if you cannot execute the request, reply with "ERROR" (without quotes).'

NL_RESPONDER_PROMPT = 'You are NaturalLanguageResponderGPT. You will receive a query from a user. ' \
    'Use the provided functions to execute what is requested and reply with a response (in natural language). ' \
    'Important: the user does not have the capacity to respond to follow-up questions, so if you think you have enough information to reply/execute the actions, do so.'
    #'If you do not have enough information to reply, if you cannot execute the request, or if the request is invalid, reply with "ERROR" (without quotes).' \


    
class Responder:
    def __init__(self, toolformer : Toolformer, memory : Storage, tools, additional_info : str):
        self.toolformer = toolformer
        self.memory = memory
        self.tools = tools
        self.additional_info = additional_info

    def reply_with_protocol_document(self, query, protocol_document, tools, additional_info):
        print('===NL RESPONDER (WITH PROTOCOL)===')

        conversation = self.toolformer.new_conversation(PROTOCOL_RESPONDER_PROMPT + additional_info, tools, category='conversation')

        prompt = 'The protocol is the following:\n\n' + protocol_document + '\n\nThe query is the following:' + query

        reply = conversation.chat(prompt, print_output=True)

        print('======')

        if 'error' in reply.lower().strip()[-10:]:
            return json.dumps({
                'status': 'error',
            })

        return json.dumps({
            'status': 'success',
            'body': reply
        })


    def reply_to_nl_query(self, query):
        print('===NL RESPONDER (NO PROTOCOL)===')
        print(NL_RESPONDER_PROMPT + self.additional_info)

        conversation = self.toolformer.new_conversation(NL_RESPONDER_PROMPT + self.additional_info, self.tools, category='conversation')

        reply = conversation.chat(query, print_output=True)
        print('======')

        if 'error' in reply.lower().strip()[-10:]:
            return json.dumps({
                'status': 'error',
            })

        return json.dumps({
            'status': 'success',
            'body': reply
        })


    def reply_to_query(self, query, protocol_id, tools, additional_info):
        print('Additional info:', additional_info)
        if protocol_id is None:
            return self.reply_to_nl_query(query, tools, additional_info)
        else:
            base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
            protocol_document = self.memory.load_protocol_document(base_folder, protocol_id)
            return self.reply_with_protocol_document(query, protocol_document, tools, additional_info)