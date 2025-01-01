from abc import ABC, abstractmethod
import requests
from typing import List

from agora.common.core import Conversation
from agora.common.errors import ProtocolTransportError

class SenderTransporter(ABC):
    @abstractmethod
    def new_conversation(self, target: str, multiround: bool, protocol_hash: str, protocol_sources: List[str]) -> Conversation:
        """
        Creates a new conversation with the target.

        Args:
            target (str): The target URL or endpoint.
            multiround (bool): Whether the conversation is multi-round.
            protocol_hash (str): The protocol's hash identifier.
            protocol_sources (List[str]): Sources referencing the protocol.

        Returns:
            Conversation: A conversation instance.
        """
        pass


class SimpleSenderTransporter(SenderTransporter):
    class SimpleExternalConversation(Conversation):
        def __init__(
            self,
            target: str,
            multiround: bool,
            protocol_hash: str,
            protocol_sources: List[str]
        ):
            """
            Initializes a simple external conversation.

            Args:
                target (str): The target URL or endpoint.
                multiround (bool): Whether multi-round communication is enabled.
                protocol_hash (str): The protocol hash.
                protocol_sources (List[str]): Protocol sources.
            """
            self.target = target
            self.multiround = multiround
            self.protocol_hash = protocol_hash
            self.protocol_sources = protocol_sources
            self._conversation_id = None

        def __call__(self, message: str):
            """
            Sends a message in the current conversation.

            Args:
                message (str): The message to send.

            Returns:
                dict: The response containing 'status' and 'body'.
            """
            if self._conversation_id is None:
                target_url = self.target
            else:
                target_url = f'{self.target}/conversations/{self._conversation_id}'

            raw_query = {
                'protocolHash': self.protocol_hash,
                'protocolSources': self.protocol_sources,
                'body': message
            }

            if self.multiround:
                raw_query['multiround'] = True

            raw_response = requests.post(target_url, json=raw_query)

            if raw_response.status_code != 200:
                raise ProtocolTransportError('Error in external conversation:', raw_response.text)
            
            response = raw_response.json()

            if self.multiround and self._conversation_id is None:
                if 'conversationId' not in response:
                    raise Exception('Multiround conversation did not return conversationId:', response)
                self._conversation_id = response['conversationId']

            return {
                'status': response['status'],
                'body': response['body']
            }
        def close(self) -> None:
            """
            Closes the conversation by deleting it from the remote service.
            """
            if self._conversation_id is not None:
                raw_response = requests.delete(f'{self.target}/conversations/{self._conversation_id}')
                if raw_response.status_code != 200:
                    raise Exception('Error in closing external conversation:', raw_response.text)

    def new_conversation(self, target: str, multiround: bool, protocol_hash: str, protocol_sources: List[str]) -> SimpleExternalConversation:
        """
        Creates a new SimpleExternalConversation instance.

        Args:
            target (str): The target URL or endpoint.
            multiround (bool): Whether the conversation is multi-round.
            protocol_hash (str): The protocol's hash identifier.
            protocol_sources (List[str]): Protocol sources.

        Returns:
            SimpleExternalConversation: A new conversation instance.
        """
        return self.SimpleExternalConversation(target, multiround, protocol_hash, protocol_sources)

