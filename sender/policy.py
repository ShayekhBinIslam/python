from sender.storage import SenderStorage

class SimpleSenderPolicy:
    def __init__(self, memory : SenderStorage, num_conversations_for_protocol, num_conversations_for_implementation):
        self.memory = memory
        self.num_conversations_for_protocol = num_conversations_for_protocol
        self.num_conversations_for_implementation = num_conversations_for_implementation
    
    def should_negotiate_protocol(self, task_id, task_data, target):
        return self.memory.get_num_conversations(task_id, target) >= self.num_conversations_for_protocol
    
    def should_implement_protocol(self, task_id, task_data, target):
        return self.memory.get_num_conversations(task_id, target) >= self.num_conversations_for_implementation