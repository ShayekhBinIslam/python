from typing import List, Optional
from agora.common.core import Suitability

from agora.common.toolformers.base import Conversation, ToolLike
from agora.common.errors import ProtocolRejectedError, ProtocolRetrievalError
from agora.common.memory import ProtocolMemory
from agora.common.storage import Storage, JSONStorage
from agora.common.executor import Executor, RestrictedExecutor
from agora.receiver.components.responder import Responder
from agora.receiver.components.protocol_checker import ReceiverProtocolChecker
from agora.receiver.components.negotiator import ReceiverNegotiator
from agora.receiver.components.programmer import ReceiverProgrammer

from agora.utils import download_and_verify_protocol, extract_metadata


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

class Receiver:
    """
    Handles receiving and processing protocols, including negotiation and execution.
    """

    def __init__(
        self,
        storage: Storage,
        responder: Responder,
        protocol_checker: ReceiverProtocolChecker,
        negotiator: ReceiverNegotiator,
        programmer: ReceiverProgrammer,
        executor: Executor,
        tools: List[ToolLike],
        additional_info: str = '',
        implementation_threshold: int = 5
    ):
        """
        Initializes the Receiver with needed components and configurations.

        Args:
            storage (Storage): Backend storage for memory.
            responder (Responder): Handles responses based on protocols.
            protocol_checker (ReceiverProtocolChecker): Checks protocol validity.
            negotiator (ReceiverNegotiator): Manages protocol negotiations.
            programmer (ReceiverProgrammer): Generates protocol implementations.
            executor (Executor): Executes protocol implementations.
            tools (List[ToolLike]): A list of available tools.
            additional_info (str, optional): Extra info used during operation.
            implementation_threshold (int, optional): Threshold for auto-generating code.
        """
        self.memory = ReceiverMemory(storage)
        self.responder = responder
        self.protocol_checker = protocol_checker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.tools = tools
        self.additional_info = additional_info
        self.implementation_threshold = implementation_threshold

    @staticmethod
    def make_default(
        toolformer,
        storage: Storage = None,
        responder: Responder = None,
        protocol_checker: ReceiverProtocolChecker = None,
        negotiator: ReceiverNegotiator = None,
        programmer: ReceiverProgrammer = None,
        executor: Executor = None,
        tools: List[ToolLike] = None,
        additional_info: str = '',
        storage_path: str = './receiver_storage.json',
        implementation_threshold: int = 5
    ) -> 'Receiver':
        """
        Creates a default Receiver instance with customizable components.

        Args:
            toolformer: The Toolformer instance.
            storage (Storage, optional): A storage backend or None to create a default.
            responder (Responder, optional): The responder component.
            protocol_checker (ReceiverProtocolChecker, optional): The protocol checker.
            negotiator (ReceiverNegotiator, optional): The negotiator component.
            programmer (ReceiverProgrammer, optional): The programmer component.
            executor (Executor, optional): The executor component.
            tools (List[ToolLike], optional): A list of tools. Defaults to empty list.
            additional_info (str, optional): Extra info. Defaults to ''.
            storage_path (str, optional): Path for JSON storage. Defaults to './receiver_storage.json'.
            implementation_threshold (int, optional): Threshold for code generation.

        Returns:
            Receiver: A configured Receiver instance.
        """
        if tools is None:
            tools = []

        if storage is None:
            storage = JSONStorage(storage_path)

        if responder is None:
            responder = Responder(toolformer)

        if protocol_checker is None:
            protocol_checker = ReceiverProtocolChecker(toolformer)

        if negotiator is None:
            negotiator = ReceiverNegotiator(toolformer)
        
        if programmer is None:
            programmer = ReceiverProgrammer(toolformer)

        if executor is None:
            executor = RestrictedExecutor()

        return Receiver(storage, responder, protocol_checker, negotiator, programmer, executor, tools, additional_info, implementation_threshold)
    
    def get_implementation(self, protocol_id: str) -> Optional[str]:
        """
        Retrieves or generates the implementation code for the given protocol.

        Args:
            protocol_id (str): The identifier of the protocol.

        Returns:
            Optional[str]: The implementation code if generated or previously stored. None if not available.
        """
        # Check if a routine exists and eventually create it
        implementation = self.memory.get_implementation(protocol_id)

        if implementation is None and self.memory.get_protocol_conversations(protocol_id) >= self.implementation_threshold:
            protocol = self.memory.get_protocol(protocol_id)
            implementation = self.programmer(self.tools, protocol.protocol_document, protocol.metadata.get('multiround', False))
            self.memory.register_implementation(protocol_id, implementation)

        return implementation

    def create_conversation(self, protocol_hash: str, protocol_sources: List[str]) -> Conversation:
        """
        Creates a new conversation based on the protocol hash and sources.

        Args:
            protocol_hash (str): Hash identifier for the protocol.
            protocol_sources (List[str]): A list of protocol source URLs.

        Returns:
            Conversation: A new conversation or negotiation session.

        Raises:
            ProtocolRetrievalError: If unable to download protocol.
            ProtocolRejectedError: If protocol is deemed inadequate.
        """
        if protocol_hash == 'negotiation':
            return self.negotiator.create_conversation(self.tools, self.additional_info)

        protocol_document = None
        implementation = None

        if protocol_hash is not None:
            self.memory.increment_protocol_conversations(protocol_hash)

            if not self.memory.is_known(protocol_hash):
                for protocol_source in protocol_sources:
                    protocol_document = download_and_verify_protocol(protocol_hash, protocol_source)
                    if protocol_document is not None:
                        break

                if protocol_document is None:
                    raise ProtocolRetrievalError('Failed to download protocol')
                
                metadata = extract_metadata(protocol_document)
                self.memory.register_new_protocol(protocol_hash, protocol_sources, protocol_document, metadata)

            protocol = self.memory.get_protocol(protocol_hash)
            protocol_document = protocol.protocol_document
            metadata = protocol.metadata

            if self.memory.get_suitability(protocol_hash) == Suitability.UNKNOWN:
                if self.protocol_checker(protocol_document, self.tools):
                    self.memory.set_suitability(protocol_hash, Suitability.ADEQUATE)
                else:
                    self.memory.set_suitability(protocol_hash, Suitability.INADEQUATE)

            if self.memory.get_suitability(protocol_hash) == Suitability.ADEQUATE:
                protocol_document = self.memory.get_protocol(protocol_hash).protocol_document
            else:
                raise ProtocolRejectedError

            implementation = self.get_implementation(protocol_hash)

        if implementation is None:
            return self.responder.create_conversation(protocol_document, self.tools, self.additional_info)
        else:
            return self.executor.new_conversation(protocol_hash, implementation, metadata.get('multiround', False), self.tools)