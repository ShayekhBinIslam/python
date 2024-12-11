from abc import ABC, abstractmethod
import json
from pathlib import Path

from common.core import Suitability
from common.storage import Storage

class ReceiverStorage(Storage):
    @abstractmethod
    def has_implementation(self, protocol_id):
        pass

    @abstractmethod
    def has_protocol_document(self, protocol_id):
        pass

    @abstractmethod
    def load_protocol_document(self, protocol_id):
        pass
    
    @abstractmethod
    def get_suitability(self, protocol_id):
        pass

    @abstractmethod
    def set_suitability(self, protocol_id, suitability):
        pass

    def is_categorized(self, protocol_id):
        return self.get_suitability(protocol_id) != Suitability.UNKNOWN
    
    @abstractmethod
    def increment_conversations(self, target):
        pass
    
    @abstractmethod
    def get_num_conversations(self, target):
        pass
    
    @abstractmethod
    def register_new_protocol(self, protocol_id, source, protocol):
        pass
    
    @abstractmethod
    def register_implementation(self, protocol_id, implementation):
        pass

    @abstractmethod
    def get_implementation_path(self, protocol_id):
        pass

class LocalReceiverStorage(ReceiverStorage):
    def __init__(self, storage_path=None):
        self.protocols = {}
        self.conversations = {}

        if storage_path is None:
            storage_path = './storage/user'
        
        storage_path = Path(storage_path)

        self.storage_path = storage_path
    
    def save_memory(self):
        with open(self.storage_path / 'memory.json', 'w') as f:
            json.dump({
                'protocols': self.protocols,
                'conversations': self.conversations
            }, f)
    
    def load_memory(self):
        with open(self.storage_path / 'memory.json', 'r') as f:
            data = json.load(f)
            self.protocols = data['protocols']
            self.conversations = data['conversations']
    
    def has_implementation(self, protocol_id):
        if protocol_id not in self.protocols:
            return False
        
        return self.protocols[protocol_id]['has_implementation']

    def get_suitability(self, protocol_id):
        if protocol_id not in self.protocols:
            return Suitability.UNKNOWN

        return self.protocols[protocol_id]['suitability_info']
    
    def set_suitability(self, protocol_id, suitability):
        self.protocols[protocol_id]['suitability_info'] = suitability

    def is_categorized(self, protocol_id):
        if protocol_id not in self.protocols:
            return False
        
        return self.protocols[protocol_id]['suitability_info'] != Suitability.UNKNOWN
    
    def increment_conversations(self, target):
        if target not in self.conversations:
            self.conversations[target] = 0
        
        self.conversations[target] += 1

    def get_num_conversations(self, target):
        if target not in self.conversations:
            return 0
        
        return self.conversations[target]
    
    def has_protocol_document(self, protocol_id):
        return protocol_id in self.protocols
    
    def register_new_protocol(self, protocol_id, source, protocol):
        self.protocols[protocol_id] = {
            'sources': [source],
            'has_implementation': {},
            'suitability_info': {}
        }

        with open(self.storage_path / 'protocol_documents' / f'{protocol_id}.json', 'w') as f:
            f.write(protocol)
    
    def register_implementation(self, protocol_id, implementation):
        if protocol_id not in self.protocols:
            return False
        
        self.protocols[protocol_id]['has_implementation'] = True

        with open(self.storage_path / 'implementations' / f'{protocol_id}.py', 'w') as f:
            f.write(implementation)

        return True
    
    def get_implementation_path(self, protocol_id):
        return self.storage_path / 'implementations' / f'{protocol_id}.py'

    def load_protocol_document(self, protocol_id):
        base_folder = self.storage_path / 'protocol_documents'
        with open(base_folder / f'{protocol_id}.json', 'r') as f:
            return f.read()
