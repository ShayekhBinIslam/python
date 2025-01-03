from typing import List

from agora.common.toolformers.base import Tool, ToolLike, Toolformer

CHECKER_TOOL_PROMPT = 'You are ProtocolCheckerGPT. Your task is to look at the provided protocol and determine if you have access ' \
    'to the tools required to implement it. A protocol is sufficiently expressive if an implementer could write code that, given a query formatted according to the protocol and the tools ' \
    'at your disposal, can parse the query according to the protocol\'s specification and send a reply. Think about it and at the end of the reply write "YES" if the' \
    'protocol is adequate or "NO". Do not attempt to implement the protocol or call the tools: that will be done by the implementer.'

class ReceiverProtocolChecker:
    """Checks protocol validity and suitability for the Receiver."""

    def __init__(self, toolformer : Toolformer):
        """Initialize the ReceiverProtocolChecker with a Toolformer.

        Args:
            toolformer (Toolformer): The Toolformer instance managing tools.
        """
        self.toolformer = toolformer
    
    def __call__(self, protocol_document : str, tools : List[ToolLike], additional_info : str = '') -> bool:
        """Determine if the protocol is suitable based on available tools.

        Args:
            protocol_document (str): The protocol document to evaluate.
            tools (List[ToolLike]): A list of tools available to implement the protocol.
            additional_info (str, optional): Additional information for evaluation. Defaults to ''.

        Returns:
            bool: True if the protocol is suitable, False otherwise.
        """
        message = 'Protocol document:\n\n' + protocol_document + '\n\n' + 'Functions that the implementer will have access to:\n\n'

        if len(tools) == 0:
            message += 'No additional functions provided'
        else:
            for tool in tools:
                tool = Tool.from_toollike(tool)
                message += str(tool) + '\n\n'

        prompt = CHECKER_TOOL_PROMPT

        if additional_info:
            prompt += '\n\n' + additional_info

        conversation = self.toolformer.new_conversation(prompt, [], category='protocolChecking')

        reply = conversation(message, print_output=False)

        # print('Reply:', reply)
        # print(reply.lower().strip()[-10:])
        # print('Parsed decision:', 'yes' in reply.lower().strip()[-10:])

        return 'yes' in reply.lower().strip()[-10:]