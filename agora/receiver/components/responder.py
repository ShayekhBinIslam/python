# The responder is a special toolformer that replies to a service based on a protocol document.
# It receives the protocol document and writes the response that must be sent to the system.

from typing import List, Optional

from agora.common.toolformers.base import Conversation, Toolformer, ToolLike

PROTOCOL_RESPONDER_PROMPT = (
    "You are ResponderGPT. Below you will find a document describing detailing how to respond to a query. "
    "The communication might involve multiple rounds of back-and-forth."
    "Use the provided functions to execute what is requested and provide the response according to the protocol's specification. "
    "Only reply with the response itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting."
)

NL_RESPONDER_PROMPT = (
    "You are NaturalLanguageResponderGPT. You will receive a query from a user. "
    "Use the provided functions to execute what is requested and reply with a response (in natural language). "
    "Important: the user does not have the capacity to respond to follow-up questions, so if you think you have enough information to reply/execute the actions, do so."
)


class Responder:
    def __init__(self, toolformer: Toolformer) -> None:
        """Initializes a new Responder.

        Args:
            toolformer (Toolformer): The Toolformer instance handling transformations.
        """
        self.toolformer = toolformer

    def create_protocol_conversation(
        self, protocol_document: str, tools: List[ToolLike], additional_info: str = ""
    ) -> Conversation:
        """Creates a protocol-based conversation.

        Args:
            protocol_document (str): The text describing the protocol.
            tools (List[ToolLike]): A list of tools available to the conversation.
            additional_info (str, optional): Additional context for the conversation.

        Returns:
            Conversation: The newly created conversation following the protocol.
        """
        # print('===NL RESPONDER (WITH PROTOCOL)===')

        prompt = PROTOCOL_RESPONDER_PROMPT

        if additional_info:
            prompt += "\n\n" + additional_info

        prompt += "\n\nThe protocol is the following:\n\n" + protocol_document

        return self.toolformer.new_conversation(prompt, tools, category="conversation")

    def create_nl_conversation(
        self, tools: List[ToolLike], additional_info: str = ""
    ) -> Conversation:
        """Creates a natural language conversation without protocol constraints.

        Args:
            tools (List[ToolLike]): Tools available during the conversation.
            additional_info (str, optional): Additional context.

        Returns:
            Conversation: The created NL conversation.
        """
        # print('===NL RESPONDER (NO PROTOCOL)===')
        # print('Preparing NL response with tools:', [tool.name for tool in tools])

        prompt = NL_RESPONDER_PROMPT

        if additional_info:
            prompt += "\n\n" + additional_info

        return self.toolformer.new_conversation(prompt, tools, category="conversation")

    def create_conversation(
        self,
        protocol_document: Optional[str],
        tools: List[ToolLike],
        additional_info: str = "",
    ) -> Conversation:
        """Creates either a protocol-based or a natural language conversation.

        Args:
            protocol_document (Optional[str]): The protocol text if available. If None, a natural language conversation is created.
            tools (List[ToolLike]): Tools for conversation handling.
            additional_info (str, optional): Additional context or configuration.

        Returns:
            Conversation: The resulting conversation instance.
        """
        if protocol_document is None:
            return self.create_nl_conversation(tools, additional_info)
        else:
            return self.create_protocol_conversation(
                protocol_document, tools, additional_info
            )
