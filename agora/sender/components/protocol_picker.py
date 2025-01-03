from typing import List, Optional, Tuple

from agora.common.core import Protocol, Suitability
from agora.sender.task_schema import TaskSchema, TaskSchemaLike
from agora.common.toolformers.base import Toolformer

CHECKER_TASK_PROMPT = 'You are ProtocolCheckerGPT. Your task is to look at the provided protocol and determine if it is expressive ' \
    'enough to fullfill the required task (of which you\'ll receive a JSON schema). A protocol is sufficiently expressive if you could write code that, given the input data, sends ' \
    'the query according to the protocol\'s specification and parses the reply. Think about it and at the end of the reply write "YES" if the' \
    'protocol is adequate or "NO"'

class ProtocolPicker:
    """Facilitates checking and selecting protocols for a given task schema."""

    def __init__(self, toolformer: Toolformer) -> None:
        """Initializes the ProtocolPicker.

        Args:
            toolformer (Toolformer): The Toolformer instance used for protocol checking.
        """
        self.toolformer = toolformer

    def check_protocol_for_task(self, protocol_document: str, task_schema: TaskSchemaLike) -> bool:
        """Checks if a given protocol is adequate for a task.

        Args:
            protocol_document (str): The protocol document text.
            task_schema (TaskSchemaLike): The task schema.

        Returns:
            bool: True if the protocol is adequate, otherwise False.
        """
        task_schema = TaskSchema.from_taskschemalike(task_schema)
        conversation = self.toolformer.new_conversation(CHECKER_TASK_PROMPT, [], category='protocolChecking')

        message = 'The protocol is the following:\n\n' + protocol_document + '\n\nThe task is the following:\n\n' + str(task_schema)

        reply = conversation(message, print_output=True)

        return 'yes' in reply.lower().strip()[-10:]

    def pick_protocol(
        self,
        task_schema: TaskSchemaLike,
        *protocol_lists: List[Protocol]
    ) -> Tuple[Optional[Protocol], dict]:
        """Selects the first adequate protocol from provided lists.

        Args:
            task_schema (TaskSchemaLike): The schema of the task.
            *protocol_lists (List[Protocol]): One or more lists of Protocol objects.

        Returns:
            (Optional[Protocol], dict): A tuple of the chosen protocol (if any)
                and a dictionary of hash evaluations.
        """
        protocol_evaluations = {}

        for protocol_list in protocol_lists:
            for protocol in protocol_list:
                if self.check_protocol_for_task(protocol.protocol_document, task_schema):
                    protocol_evaluations[protocol.hash] = Suitability.ADEQUATE
                    return protocol, protocol_evaluations
                else:
                    protocol_evaluations[protocol.hash] = Suitability.INADEQUATE

        return None, protocol_evaluations