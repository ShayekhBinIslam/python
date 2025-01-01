from abc import ABC, abstractmethod
from collections.abc import MutableMapping
import json
from pathlib import Path
from typing import Any, Iterator

class Storage(ABC, MutableMapping):
    """Abstract base class for a key-value storage.

    This class extends both the 'ABC' class and the 'MutableMapping' interface.
    """

    @abstractmethod
    def save_memory(self) -> None:
        """Saves current state to the underlying storage mechanism."""
        pass
    
    @abstractmethod
    def load_memory(self) -> None:
        """Loads state from the underlying storage mechanism."""
        pass


class JSONStorage(Storage):
    """A JSON-based storage implementation."""

    def __init__(self, storage_path: str, autosave: bool = True) -> None:
        """Instantiates JSONStorage.

        Args:
            storage_path (str): Path to the JSON file.
            autosave (bool): If True, saves automatically after updates.
        """
        self.storage_path = Path(storage_path)
        self.data = {}
        self.load_memory()

        self.autosave = autosave

    def save_memory(self) -> None:
        """Saves current state to the JSON file."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def load_memory(self) -> None:
        """Loads the state from the JSON file."""
        if not self.storage_path.exists():
            self.save_memory()
        with open(self.storage_path, 'r') as f:
            self.data = json.load(f)

    def __getitem__(self, key: str) -> Any:
        """Retrieves an item by key.

        Args:
            key (str): Key to retrieve.

        Returns:
            Any: The stored value or None if not found.
        """
        return self.data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Sets a value for the specified key.

        Args:
            key (str): Key to modify.
            value (Any): The data to store.
        """
        self.data[key] = value

        if self.autosave:
            self.save_memory()

    def __delitem__(self, key: str) -> None:
        """Deletes the entry associated with the specified key.

        Args:
            key (str): Key to delete.
        """
        del self.data[key]

        if self.autosave:
            self.save_memory()
    
    def __iter__(self) -> Iterator[str]:
        """Iterates over stored keys.

        Returns:
            Iterator[str]: An iterator over the keys.
        """
        return iter(self.data)
    
    def __len__(self) -> int:
        """Returns the number of stored items.

        Returns:
            int: The count of items.
        """
        return len(self.data)
    
    def __contains__(self, key: object) -> bool:
        """Checks if a key is contained.

        Args:
            key (object): Key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        return key in self.data
    
    def __str__(self) -> str:
        """Returns a string representation of this storage.

        Returns:
            str: String describing the JSONStorage path.
        """
        return f'JSONStorage({self.storage_path})'