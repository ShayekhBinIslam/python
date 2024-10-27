from enum import Enum
import json
from pathlib import Path

class Suitability(str, Enum):
    ADEQUATE = 'adequate'
    INADEQUATE = 'inadequate'
    PROBABLY_INADEQUATE = 'probably_inadequate'
    UNKNOWN = 'unknown'


class SenderStorage:
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
    
    def has_implementation(self, task_type, protocol_id):
        if protocol_id not in self.protocols:
            return False

        if task_type not in self.protocols[protocol_id]['has_implementation']:
            return False
        
        return self.protocols[protocol_id]['has_implementation'][task_type]

    def is_adequate(self, task_type, protocol_id):
        if protocol_id not in self.protocols:
            return False
        
        if task_type not in self.protocols[protocol_id]['suitability_info']:
            return False

        return self.protocols[protocol_id]['suitability_info'][task_type] == Suitability.ADEQUATE

    def is_categorized(self, task_type, protocol_id):
        if protocol_id not in self.protocols:
            return False
        
        if task_type not in self.protocols[protocol_id]['suitability_info']:
            return False
        
        return self.protocols[protocol_id]['suitability_info'][task_type] != Suitability.UNKNOWN
    
    def increment_conversations(self, task_id, task_data, target):
        if task_id not in self.conversations:
            self.conversations[task_id] = {}
        if target not in self.conversations[task_id]:
            self.conversations[task_id][target] = 0
        
        self.conversations[task_id][target] += 1

        # task_data isn't used

    def get_num_conversations(self, task_id, target):
        if task_id not in self.conversations:
            return 0
        if target not in self.conversations[task_id]:
            return 0
        
        return self.conversations[task_id][target]
    
    def register_new_protocol(self, protocol_id, source, protocol):
        self.protocols[protocol_id] = {
            'sources': [source],
            'has_implementation': {},
            'suitability_info': {}
        }

        with open(self.storage_path / 'protocol_documents' / f'{protocol_id}.json', 'w') as f:
            f.write(protocol)
    
    def register_implementation(self, protocol_id, task_id, implementation):
        if protocol_id not in self.protocols:
            return False
        
        self.protocols[protocol_id]['has_implementation'][task_id] = True

        with open(self.storage_path / 'implementations' / f'{protocol_id}_{task_id}.py', 'w') as f:
            f.write(implementation)

        return True
    
    def get_implementation_path(self, protocol_id, task_id):
        return self.storage_path / 'implementations' / f'{protocol_id}_{task_id}.py'

    def load_protocol_document(self, protocol_id):
        base_folder = self.storage_path / 'protocol_documents'
        with open(base_folder / f'{protocol_id}.json', 'r') as f:
            return f.read()
