from typing import Optional

from agora.common.core import Protocol, Suitability
from agora.common.errors import StorageError
from agora.common.memory import ProtocolMemory
from agora.common.storage import Storage


class SenderMemory(ProtocolMemory):
    """
    Manages the memory for the Sender, including protocol suitability and task conversations.
    """

    def __init__(self, storage: Storage):
        """
        Initializes SenderMemory with a storage backend.

        Args:
            storage (Storage): The storage backend for memory.
        """
        super().__init__(storage, num_conversations={})

    def get_suitability(
        self, protocol_id: str, task_id: str, target: Optional[str]
    ) -> Suitability:
        """
        Retrieves the suitability status for a given protocol ID and task ID.

        Args:
            protocol_id (str): The protocol identifier.
            task_id (str): The task identifier.
            target (Optional[str]): The target system or service.

        Returns:
            Suitability: The stored suitability status.
        """
        suitability_info = super().get_extra_field(protocol_id, "suitability", {})

        if task_id not in suitability_info:
            return Suitability.UNKNOWN

        if target is not None and target in suitability_info[task_id]["overrides"]:
            return suitability_info[task_id]["overrides"][target]

        return suitability_info[task_id]["default"]

    def get_known_suitable_protocol_ids(self, task_id, target):
        """
        Returns known suitable protocol IDs for the given task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            list: A list of known suitable protocol IDs.
        """
        suitable_protocols = []
        for protocol_id in self.protocol_ids():
            if (
                self.get_suitability(protocol_id, task_id, target)
                == Suitability.ADEQUATE
            ):
                suitable_protocols.append(protocol_id)

        return suitable_protocols

    def get_suitable_protocol(self, task_id, target) -> Optional[Protocol]:
        """
        Retrieves a suitable protocol object for the given task and target if available.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            Optional[Protocol]: The first suitable protocol found or None if none available.
        """
        suitable_protocols = self.get_known_suitable_protocol_ids(task_id, target)
        if len(suitable_protocols) == 0:
            return None
        return self.get_protocol(suitable_protocols[0])

    def increment_task_conversations(self, task_id, target):
        """
        Increments the conversation counter for a given task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.
        """
        if "num_conversations" not in self.storage:
            self.storage["num_conversations"] = {}
        if task_id not in self.storage["num_conversations"]:
            self.storage["num_conversations"][task_id] = {}
        if target not in self.storage["num_conversations"][task_id]:
            self.storage["num_conversations"][task_id][target] = 0
        self.storage["num_conversations"][task_id][target] += 1

        self.storage.save_memory()

    def get_task_conversations(self, task_id, target):
        """
        Retrieves the number of stored conversations for a task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            int: The number of conversations.
        """
        if "num_conversations" not in self.storage:
            return 0
        if task_id not in self.storage["num_conversations"]:
            return 0
        if target not in self.storage["num_conversations"][task_id]:
            return 0
        return self.storage["num_conversations"][task_id][target]

    def increment_protocol_conversations(self, protocol_id):
        """
        Increments the conversation counter for a given protocol.

        Args:
            protocol_id: The protocol identifier.
        """
        num_conversations = self.get_protocol_conversations(protocol_id)
        self.set_extra_field(protocol_id, "conversations", num_conversations + 1)

    def get_protocol_conversations(self, protocol_id):
        """
        Retrieves the number of stored conversations for a protocol.

        Args:
            protocol_id: The protocol identifier.

        Returns:
            int: The number of conversations.
        """
        return self.get_extra_field(protocol_id, "conversations", 0)

    def has_suitable_protocol(self, task_id, target):
        """
        Checks whether a suitable protocol exists for a given task and target.

        Args:
            task_id: The task identifier.
            target: The target system or service.

        Returns:
            bool: True if a suitable protocol exists, otherwise False.
        """
        return len(self.get_known_suitable_protocol_ids(task_id, target)) > 0

    def get_unclassified_protocols(self, task_id):
        """Get protocols that have not been classified for a specific task.

        Args:
            task_id: The identifier of the task.

        Returns:
            List[str]: A list of unclassified protocol IDs.
        """
        unclassified_protocols = []
        for protocol_id in self.protocol_ids():
            if self.get_suitability(protocol_id, task_id, None) == Suitability.UNKNOWN:
                unclassified_protocols.append(protocol_id)

        return unclassified_protocols

    def set_default_suitability(
        self, protocol_id: str, task_id: str, suitability: Suitability
    ):
        """Set the default suitability for a protocol and task.

        Args:
            protocol_id (str): The identifier of the protocol.
            task_id (str): The identifier of the task.
            suitability (Suitability): The default suitability status to set.
        """
        suitability_info = self.get_extra_field(protocol_id, "suitability", {})

        if task_id not in suitability_info:
            suitability_info[task_id] = {
                "default": Suitability.UNKNOWN,
                "overrides": {},
            }

        suitability_info[task_id]["default"] = suitability

        self.set_extra_field(protocol_id, "suitability", suitability_info)

    def set_suitability_override(
        self, protocol_id: str, task_id: str, target: str, suitability: Suitability
    ):
        """Override the suitability of a protocol for a specific task and target.

        Args:
            protocol_id (str): The identifier of the protocol.
            task_id (str): The identifier of the task.
            target (str): The target for which the suitability is overridden.
            suitability (Suitability): The overridden suitability status.
        """
        suitability_info = self.get_extra_field(protocol_id, "suitability", {})

        if task_id not in suitability_info:
            suitability_info[task_id] = {
                "default": Suitability.UNKNOWN,
                "overrides": {},
            }

        suitability_info[task_id]["overrides"][target] = suitability
        self.set_extra_field(protocol_id, "suitability", suitability_info)

    def register_new_protocol(
        self, protocol_id: str, protocol_document: str, sources: list, metadata: dict
    ):
        """Register a new protocol with the given sources, document, and metadata.

        Args:
            protocol_id (str): The identifier of the new protocol.
            protocol_document (str): The document describing the protocol.
            sources (list): A list of sources where the protocol is referenced.
            metadata (dict): Additional metadata related to the protocol.
        """
        if protocol_id in self.storage["protocols"]:
            raise StorageError("Protocol already in memory:", protocol_id)

        super().register_new_protocol(
            protocol_id, protocol_document, sources, metadata, None, suitability={}
        )
