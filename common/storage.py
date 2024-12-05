from abc import ABC, abstractmethod
import json
from pathlib import Path

class Storage(ABC):
    @abstractmethod
    def save_memory(self):
        pass
    
    @abstractmethod
    def load_memory(self):
        pass
  

    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def set(self, key, value):
        pass

class JSONStorage(Storage):
    def __init__(self, storage_path, autosave=True):
        self.storage_path = Path(storage_path)
        self.data = {}
        self.load_memory()

        self.autosave = autosave

    def save_memory(self):
        with open(self.storage_path / 'memory.json', 'w') as f:
            json.dump(self.data, f)

    def load_memory(self):
        with open(self.storage_path / 'memory.json', 'r') as f:
            self.data = json.load(f)

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

        if self.autosave:
            self.save_memory()