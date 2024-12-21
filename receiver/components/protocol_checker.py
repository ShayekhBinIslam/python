from typing import List

from common.toolformers.base import ToolLike, Toolformer

CHECKER_TOOL_PROMPT = 'You are ProtocolCheckerGPT. Your task is to look at the provided protocol and determine if you have access ' \
    'to the tools required to implement it. A protocol is sufficiently expressive if an implementer could write code that, given a query formatted according to the protocol and the tools ' \
    'at your disposal, can parse the query according to the protocol\'s specification and send a reply. Think about it and at the end of the reply write "YES" if the' \
    'protocol is adequate or "NO". Do not attempt to implement the protocol or call the tools: that will be done by the implementer.'

class ReceiverProtocolChecker:
    def __init__(self, toolformer : Toolformer):
        self.toolformer = toolformer
    
    def __call__(self, protocol_document : str, tools : List[ToolLike], additional_info : str = ''):
        message = 'Protocol document:\n\n' + protocol_document + '\n\n' + 'Functions that the implementer will have access to:\n\n'

        if len(tools) == 0:
            message += 'No additional functions provided'
        else:
            for tool in tools:
                message += tool.as_documented_python() + '\n\n'

        prompt = CHECKER_TOOL_PROMPT

        if additional_info:
            prompt += '\n\n' + additional_info

        conversation = self.toolformer.new_conversation(prompt, [], category='protocolChecking')

        reply = conversation(message, print_output=True)

        print('Reply:', reply)
        print(reply.lower().strip()[-10:])
        print('Parsed decision:', 'yes' in reply.lower().strip()[-10:])

        return 'yes' in reply.lower().strip()[-10:]