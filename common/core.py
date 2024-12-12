from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List
from utils import compute_hash

class Suitability(str, Enum):
    ADEQUATE = 'adequate'
    INADEQUATE = 'inadequate'
    PROBABLY_ADEQUATE = 'probably_adequate'
    PROBABLY_INADEQUATE = 'probably_inadequate'
    UNKNOWN = 'unknown'

class Conversation(ABC):
    @abstractmethod
    def __call__(self, message, print_output=True):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class Protocol:
    def __init__(self, protocol_document : str, sources : List[str], metadata : Dict[str, str]):
        self.protocol_document = protocol_document
        self.sources = sources
        self.metadata = metadata

    @property
    def hash(self):
        return compute_hash(self.protocol_document)
    
    def __str__(self):
        return f'Protocol {self.hash}\nSources: {self.sources}\nMetadata: {self.metadata}\n\n{self.protocol_document}\n\n'