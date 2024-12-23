from typing import List, Optional

from common.core import Protocol
from common.storage import Storage
from common.errors import StorageError

class ProtocolMemory:
    def __init__(self, storage : Storage, **kwargs):
        self.storage = storage

        self.storage.load_memory()

        if 'protocols' not in self.storage:
            self.storage['protocols'] = {}

        for key, value in kwargs.items():
            self.storage[key] = value

        self.storage.save_memory()

    def protocol_ids(self):
        return list(self.storage['protocols'].keys())

    def is_known(self, protocol_id : str):
        return protocol_id in self.storage['protocols']
    
    def register_new_protocol(self, protocol_id : str, protocol_document : str, sources : List[str], metadata : dict, implementation : Optional[str] = None, **kwargs):
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

    def get_protocol(self, protocol_id):
        if 'protocols' not in self.storage:
            return None
        if protocol_id not in self.storage['protocols']:
            return None

        protocol_info = self.storage['protocols'][protocol_id]

        return Protocol(protocol_info['document'], protocol_info['sources'], protocol_info['metadata'])
    
    def get_implementation(self, protocol_id):
        if protocol_id not in self.storage['protocols']:
            return None
        return self.storage['protocols'][protocol_id]['implementation']
    
    def register_implementation(self, protocol_id, implementation):
        if protocol_id not in self.storage['protocols']:
            raise StorageError('Protocol not in memory:', protocol_id)
        self.storage['protocols'][protocol_id]['implementation'] = implementation
        self.storage.save_memory()

    def get_extra_field(self, protocol_id, field, default = None):
        if protocol_id not in self.storage['protocols']:
            return default
        return self.storage['protocols'][protocol_id].get(field, default)
    
    def set_extra_field(self, protocol_id, field, value):
        if protocol_id not in self.storage['protocols']:
            raise StorageError('Protocol not in memory:', protocol_id)
        self.storage['protocols'][protocol_id][field] = value
        self.storage.save_memory()