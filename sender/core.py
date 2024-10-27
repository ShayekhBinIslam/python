from sender.memory import SenderMemory
from sender.negotiator import SenderNegotiator
from sender.policy import SimpleSenderPolicy
from sender.programmer import SenderProgrammer
from sender.protocol_picker import ProtocolPicker
from sender.querier import Querier
from sender.executor import Executor

class Sender:
    def __init__(self, memory : SenderMemory, protocol_picker : ProtocolPicker, negotiator : SenderNegotiator, programmer : SenderProgrammer, executor : Executor, querier : Querier, policy : SimpleSenderPolicy):
        self.memory = memory
        self.protocol_picker = protocol_picker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.querier = querier
        self.policy = policy

    def execute_task(self, task_id, task_schema, task_data, target):
        suitable_protocol = self.protocol_picker.get_suitable_protocol(task_id, task_schema)
        self.memory.increment_conversations(task_id, task_data, target)

        if suitable_protocol is None:
            if self.policy.should_negotiate_protocol(task_id, task_data, target):
                protocol_data = self.negotiator.negotiate_protocol_for_task(task_schema, target)
                # TODO: Upload the protocol to the network
                self.memory.register_new_protocol(protocol_data['id'], protocol_data['source'], protocol_data['document'])
                suitable_protocol = protocol_data['id']

        if suitable_protocol is None:
            return self.querier.send_query_without_protocol(task_schema, task_data, target)
        else:
            if self.memory.has_implementation(suitable_protocol):
                routine_path = self.memory.get_implementation_path(suitable_protocol)
                return self.executor.run_routine(routine_path, task_schema, task_data, target, suitable_protocol)
            else:
                self.policy.increment_conversations(task_id, task_data, target)

            if self.policy.should_implement_protocol(task_id, task_data, target):
                implementation = self.programmer.write_routine_for_task(task_schema, suitable_protocol['document'])
                #self.network.send_protocol_document(protocol_document, target)
                self.memory.register_implementation(suitable_protocol, task_id, implementation)

                return self.executor.execute_task(task_schema, task_data, target, suitable_protocol)
            else:
                return self.querier.send_query_with_protocol(task_schema, task_data, target, suitable_protocol['id'], suitable_protocol['source'])