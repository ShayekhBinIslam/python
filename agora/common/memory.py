from typing import List, Optional

from agora.common.core import Protocol
from agora.common.storage import Storage
from agora.common.errors import StorageError

class ProtocolMemory:
    """Manages protocol-related memory, including registration and retrieval of protocols and their implementations."""

    def __init__(self, storage: Storage, **kwargs):
        """
        Initializes ProtocolMemory with the given storage and additional keyword arguments.

        Args:
            storage (Storage): The storage backend to use for managing protocols.
            **kwargs: Additional keyword arguments to store.
        """
        self.storage = storage

        self.storage.load_memory()

        if 'protocols' not in self.storage:
            self.storage['protocols'] = {}

        for key, value in kwargs.items():
            self.storage[key] = value

        self.storage.save_memory()

    def protocol_ids(self) -> List[str]:
        """
        Returns a list of registered protocol IDs.

        Returns:
            List[str]: A list containing all registered protocol identifiers.
        """
        return list(self.storage['protocols'].keys())

    def is_known(self, protocol_id: str) -> bool:
        """
        Checks if a protocol ID is known (registered).

        Args:
            protocol_id (str): The protocol identifier to check.

        Returns:
            bool: True if the protocol is registered, False otherwise.
        """
        return protocol_id in self.storage['protocols']
    
    def register_new_protocol(
        self,
        protocol_id: str,
        protocol_document: str,
        sources: List[str],
        metadata: dict,
        implementation: Optional[str] = None,
        **kwargs
    ):
        """
        Registers a new protocol with the specified details.

        Args:
            protocol_id (str): The identifier of the new protocol.
            protocol_document (str): The document describing the protocol.
            sources (List[str]): A list of sources where the protocol is referenced.
            metadata (dict): Additional metadata related to the protocol.
            implementation (Optional[str], optional): The implementation code associated with the protocol. Defaults to None.
            **kwargs: Additional keyword arguments to store with the protocol.

        Raises:
            StorageError: If the protocol is already registered.
        """
        if protocol_id in self.storage['protocols']:
            raise StorageError('Protocol already in memory:', protocol_id)
        
        protocol_info = {
            'document': protocol_document,
            'sources': sources,
            'metadata': metadata,
            'implementation': implementation
        }

        protocol_info.update(kwargs)

        self.storage['protocols'][protocol_id] = protocol_info
        self.storage.save_memory()

    def get_protocol(self, protocol_id: str) -> Optional[Protocol]:
        """
        Retrieves a Protocol object based on the protocol ID.

        Args:
            protocol_id (str): The identifier of the protocol to retrieve.

        Returns:
            Optional[Protocol]: The Protocol object if found, else None.
        """
        if 'protocols' not in self.storage:
            return None
        if protocol_id not in self.storage['protocols']:
            return None

        protocol_info = self.storage['protocols'][protocol_id]

        return Protocol(protocol_info['document'], protocol_info['sources'], protocol_info['metadata'])
    
    def get_implementation(self, protocol_id: str) -> Optional[str]:
        """
        Gets the implementation associated with a given protocol ID.

        Args:
            protocol_id (str): The identifier of the protocol.

        Returns:
            Optional[str]: The implementation code if available, else None.
        """
        if protocol_id not in self.storage['protocols']:
            return None
        return self.storage['protocols'][protocol_id]['implementation']
    
    def register_implementation(self, protocol_id: str, implementation: str):
        """
        Registers an implementation for a specific protocol ID.

        Args:
            protocol_id (str): The identifier of the protocol.
            implementation (str): The implementation code to associate with the protocol.

        Raises:
            StorageError: If the protocol is not registered.
        """
        if protocol_id not in self.storage['protocols']:
            raise StorageError('Protocol not in memory:', protocol_id)
        self.storage['protocols'][protocol_id]['implementation'] = implementation
        self.storage.save_memory()

    def get_extra_field(self, protocol_id: str, field: str, default=None):
        """
        Retrieves an extra field from a protocol's information.

        Args:
            protocol_id (str): The identifier of the protocol.
            field (str): The field name to retrieve.
            default: The default value to return if the field is not present. Defaults to None.

        Returns:
            Any: The value of the specified field, or the default if not found.
        """
        if protocol_id not in self.storage['protocols']:
            return default
        return self.storage['protocols'][protocol_id].get(field, default)
    
    def set_extra_field(self, protocol_id: str, field: str, value):
        """
        Sets an extra field in a protocol's information.

        Args:
            protocol_id (str): The identifier of the protocol.
            field (str): The field name to set.
            value: The value to assign to the field.

        Raises:
            StorageError: If the protocol is not registered.
        """
        if protocol_id not in self.storage['protocols']:
            raise StorageError('Protocol not in memory:', protocol_id)
        self.storage['protocols'][protocol_id][field] = value
        self.storage.save_memory()