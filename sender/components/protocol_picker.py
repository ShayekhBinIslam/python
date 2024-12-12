import json
from typing import List

from common.core import Protocol, Suitability
from toolformers.base import Toolformer

CHECKER_TASK_PROMPT = 'You are ProtocolCheckerGPT. Your task is to look at the provided protocol and determine if it is expressive ' \
    'enough to fullfill the required task (of which you\'ll receive a JSON schema). A protocol is sufficiently expressive if you could write code that, given the input data, sends ' \
    'the query according to the protocol\'s specification and parses the reply. Think about it and at the end of the reply write "YES" if the' \
    'protocol is adequate or "NO"'

class ProtocolPicker:
    def __init__(self, toolformer : Toolformer):
        self.toolformer = toolformer

    def check_protocol_for_task(self, protocol_document : str, task_schema):

        conversation = self.toolformer.new_conversation(CHECKER_TASK_PROMPT, [], category='protocolChecking')

        message = 'The protocol is the following:\n\n' + protocol_document + '\n\nThe task is the following:\n\n' + json.dumps(task_schema)

        reply = conversation(message, print_output=True)

        return 'yes' in reply.lower().strip()[-10:]

    def pick_protocol(self, task_schema, *protocol_lists : List[Protocol]):
        # TODO: Prefiltering

        protocol_evaluations = {}

        for protocol_list in protocol_lists:
            for protocol in protocol_list:
                if self.check_protocol_for_task(protocol.protocol_document, task_schema):
                    protocol_evaluations[protocol.hash] = Suitability.ADEQUATE
                    return protocol, protocol_evaluations
                else:
                    protocol_evaluations[protocol.hash] = Suitability.INADEQUATE

        return None, protocol_evaluations