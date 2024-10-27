class ProtocolPicker:
    pass

class Sender:
    def __init__(self, memory, protocol_picker, negotiator, programmer, executor, querier, policy):
        self.memory = memory
        self.protocol_picker = protocol_picker
        self.negotiator = negotiator
        self.programmer = programmer
        self.executor = executor
        self.querier = querier
        self.policy = policy

    def execute_task(self, task_id, task_data, target, task_schema=None):
        #if task_schema is None:
        #    task_schema = self.memory.get_task_schema(task_id)

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
            if self.executor.has_implementation(suitable_protocol):
                return self.executor.execute_task(task_schema, task_data, target, suitable_protocol)
            else:
                self.policy.increment_conversations(task_id, task_data, target)

            if self.policy.should_implement_protocol(task_id, task_data, target):
                implementation = self.programmer.write_routine_for_task(task_schema, suitable_protocol['document'])
                #self.network.send_protocol_document(protocol_document, target)
                self.memory.register_implementation(suitable_protocol, implementation)

                return self.executor.execute_task(task_schema, task_data, target, suitable_protocol)
            else:
                return self.querier.send_query_with_protocol(task_schema, task_data, target, suitable_protocol['id'], suitable_protocol['source'])