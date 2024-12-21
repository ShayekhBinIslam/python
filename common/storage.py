from abc import ABC, abstractmethod
from collections.abc import MutableMapping
import json
from pathlib import Path

class Storage(ABC, MutableMapping):
    @abstractmethod
    def save_memory(self):
        pass
    
    @abstractmethod
    def load_memory(self):
        pass


class JSONStorage(Storage):
    def __init__(self, storage_path, autosave=True):
        self.storage_path = Path(storage_path)
        self.data = {}
        self.load_memory()

        self.autosave = autosave

    def save_memory(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def load_memory(self):
        if not self.storage_path.exists():
            self.save_memory()
        with open(self.storage_path, 'r') as f:
            self.data = json.load(f)

    def __getitem__(self, key):
        return self.data.get(key)

    def __setitem__(self, key, value):
        self.data[key] = value

        if self.autosave:
            self.save_memory()

    def __delitem__(self, key):
        del self.data[key]

        if self.autosave:
            self.save_memory()
    
    def __iter__(self):
        return iter(self.data)
    
    def __len__(self):
        return len(self.data)
    
    def __contains__(self, key):
        return key in self.data
    
    def __repr__(self):
        return f'JSONStorage({self.storage_path})'