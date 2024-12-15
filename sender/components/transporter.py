from abc import ABC, abstractmethod
import requests

from common.core import Conversation

class SenderTransporter(ABC):
    @abstractmethod
    def new_conversation(self, target, multiround, protocol_hash, protocol_sources) -> Conversation:
        pass


class SimpleSenderTransporter(SenderTransporter):
    class SimpleExternalConversation(Conversation):
        def __init__(self, target, multiround, protocol_hash, protocol_sources):
            self.target = target
            self.multiround = multiround
            self.protocol_hash = protocol_hash
            self.protocol_sources = protocol_sources
            self._conversation_id = None

        def __call__(self, query):
            if self._conversation_id is None:
                target_url = self.target
            else:
                target_url = f'{self.target}/conversations/{self._conversation_id}'

            raw_query = {
                'protocolHash': self.protocol_hash,
                'protocolSources': self.protocol_sources,
                'body': query
            }

            if self.multiround:
                raw_query['multiround'] = True

            raw_response = requests.post(target_url, json=raw_query)

            if raw_response.status_code != 200:
                raise Exception('Error in external conversation:', raw_response.text)
            
            response = raw_response.json()

            if self.multiround and self._conversation_id is None:
                if 'conversationId' not in response:
                    raise Exception('Multiround conversation did not return conversationId:', response)
                self._conversation_id = response['conversationId']

            return {
                'status': response['status'],
                'body': response['body']
            }
        def close(self):
            if self._conversation_id is not None:
                raw_response = requests.delete(f'{self.target}/conversations/{self._conversation_id}')
                if raw_response.status_code != 200:
                    raise Exception('Error in closing external conversation:', raw_response.text)

    def new_conversation(self, target, multiround, protocol_hash, protocol_sources) -> SimpleExternalConversation:
        return self.SimpleExternalConversation(target, multiround, protocol_hash, protocol_sources)

