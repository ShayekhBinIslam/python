from typing import List

from common.core import Conversation
from common.toolformers.base import Tool, ToolLike
from common.toolformers.base import Toolformer

NEGOTIATION_RULES = '''
Here are some rules (that should also be explained to the other GPT):
- You can assume that the protocol has a sender and a receiver. Do not worry about how the messages will be delivered, focus only on the content of the messages.
- Keep the protocol short and simple. It should be easy to understand and implement.
- The protocol must specify the exact format of what is sent and received. Do not leave it open to interpretation.
- The implementation will be written by a programmer that does not have access to the negotiation process, so make sure the protocol is clear and unambiguous.
- The implementation will receive a string and return a string, so structure your protocol accordingly.
- The other party might have a different internal data schema or set of tools, so make sure that the protocol is flexible enough to accommodate that.
- Keep the negotiation short: no need to repeat the same things over and over.
- If the other party has proposed a protocol and you're good with it, there's no reason to keep negotiating or to repeat the protocol to the other party.
- Do not restate parts of the protocols that have already been agreed upon.
And remember: keep the protocol as simple and unequivocal as necessary. The programmer that will implement the protocol can code, but they are not a mind reader.
'''

TOOLS_NEGOTIATOR_PROMPT = f'''
You are ProtocolNegotiatorGPT. You are negotiating a protocol on behalf of a web service that can perform a task.
The other party is a GPT that is negotiating on behalf of the user. Your goal is to negotiate a protocol that is simple and clear, \
but also expressive enough to allow the service to perform the task. A protocol is sufficiently expressive if you could write code \
that, given the query formatted according to the protocol and the tools at the service's disposal, can parse the query according to \
the protocol's specification, perform the task (if any) and send a reply.
{NEGOTIATION_RULES}
You will receive a list of tools that are available to the programmer that will implement the protocol.
When you are okay with the protocol, don't further repeat everything, just tell to the other party that you are done.
'''

class ReceiverNegotiator:
    """Manages protocol negotiations for the Receiver."""

    def __init__(self, toolformer: Toolformer):
        """Initialize the ReceiverNegotiator with a Toolformer.

        Args:
            toolformer (Toolformer): The Toolformer instance managing tools.
        """
        self.toolformer = toolformer

    def create_conversation(self, tools: List[ToolLike], additional_info: str = '') -> Conversation:
        """Create a new negotiation conversation based on available tools.

        Args:
            tools (List[ToolLike]): A list of tools available for negotiation.
            additional_info (str, optional): Additional information for the negotiation. Defaults to ''.

        Returns:
            Conversation: A Conversation instance managing the negotiation.
        """
        prompt = TOOLS_NEGOTIATOR_PROMPT

        if additional_info:
            prompt += '\n\n' + additional_info

        prompt += '\n\nThe tools that the implementer will have access to are:\n\n'

        if len(tools) == 0:
            prompt += 'No additional tools provided'
        else:
            for tool in tools:
                tool = Tool.from_toollike(tool)
                prompt += tool.as_documented_python() + '\n\n'

        return self.toolformer.new_conversation(prompt, tools, category='negotiation')
