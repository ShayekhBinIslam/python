from typing import List

from agora.common.core import Suitability
from agora.common.memory import ProtocolMemory

class ReceiverMemory(ProtocolMemory):
    """
    Manages memory for the Receiver, including protocol registrations and suitability assessments.
    """

    def register_new_protocol(self, protocol_id: str, protocol_sources: List[str], protocol_document: str, metadata: dict):
        """
        Registers a new protocol with given sources, document, and metadata.

        Args:
            protocol_id (str): The identifier of the protocol.
            protocol_sources (List[str]): A list of source URLs for the protocol.
            protocol_document (str): The protocol contents.
            metadata (dict): Additional protocol metadata.
        """
        super().register_new_protocol(
            protocol_id,
            protocol_document,
            protocol_sources,
            metadata,
            None,
            suitability=Suitability.UNKNOWN,
            conversations=0
        )
    
    def get_protocol_conversations(self, protocol_id: str) -> int:
        """
        Returns the number of conversations associated with a protocol.

        Args:
            protocol_id (str): The protocol's identifier.

        Returns:
            int: The conversation count.
        """
        return self.get_extra_field(protocol_id, 'conversations', 0)
    
    def increment_protocol_conversations(self, protocol_id: str) -> None:
        """
        Increments the conversation count for the specified protocol.

        Args:
            protocol_id (str): The identifier of the protocol.
        """
        self.set_extra_field(protocol_id, 'conversations', self.get_protocol_conversations(protocol_id) + 1)

    def set_suitability(self, protocol_id: str, suitability: Suitability) -> None:
        """
        Sets the suitability for a given protocol.

        Args:
            protocol_id (str): The identifier of the protocol.
            suitability (Suitability): The new suitability value.
        """
        super().set_extra_field(protocol_id, 'suitability', suitability)

    def get_suitability(self, protocol_id: str) -> Suitability:
        """
        Retrieves the suitability for a given protocol.

        Args:
            protocol_id (str): The protocol's identifier.

        Returns:
            Suitability: The current suitability status.
        """
        return self.get_extra_field(protocol_id, 'suitability', Suitability.UNKNOWN)