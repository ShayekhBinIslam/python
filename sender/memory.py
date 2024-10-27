from enum import Enum

class Suitability(str, Enum):
    ADEQUATE = 'adequate'
    INADEQUATE = 'inadequate'
    PROBABLY_INADEQUATE = 'probably_inadequate'
    UNKNOWN = 'unknown'


class SenderMemory:
    def __init__(self):
        self.protocols = {}
        self.conversations = {}
    
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
