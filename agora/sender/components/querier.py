# The querier queries a service based on a protocol document.
# It receives the protocol document and writes the query that must be performed to the system.

import json
from typing import Any, Callable, Dict

from agora.sender.task_schema import TaskSchema, TaskSchemaLike
from agora.common.errors import ExecutionError, ProtocolRejectedError
from agora.common.toolformers.base import Toolformer, Tool

PROTOCOL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You act as an intermediary between a machine (who has a very specific input and output schema) and an external service (which follows a very specific protocol).' \
    'You will receive a task description (including a schema of the input and output that the machine uses) and the corresponding data. Call the \"send_query\" tool with a message following the protocol.' \
    'Do not worry about managing communication, everything is already set up for you. Just focus on sending the right message.' \
    'The send_query tool will return the reply of the service.\n' \
    'Some protocols may explictly require multiple queries. In that case, you can call send_query multiple times. Otherwise, call it only once. \n' \
    'In any case, you cannot call send_query more than {max_queries} time(s), no matter what the protocol says.' \
    'Once you receive the reply, call the "deliverStructuredOutput" tool with parameters according to the task\'s output schema. \n' \
    'You cannot call deliverStructuredOutput multiple times, so make sure to deliver the right output the first time.' \
    'If there is an error and the machine\'s input/output schema specifies how to handle an error, return the error in that format. Otherwise, call the "error" tool.' \

def construct_query_description(protocol_document: str, task_schema: TaskSchemaLike, task_data: Any) -> str:
    """Constructs a query description for the protocol and task.

    Args:
        protocol_document (str): The protocol document text.
        task_schema (TaskSchemaLike): The schema for the task.
        task_data (Any): The data for the task.

    Returns:
        str: The constructed query description.
    """
    query_description = ''
    if protocol_document is not None:
        query_description += 'Protocol document:\n\n'
        query_description += protocol_document + '\n\n'

    task_schema = TaskSchema.from_taskschemalike(task_schema).to_json()
    query_description += 'JSON schema of the task:\n\n'
    query_description += 'Input (i.e. what the machine will provide you):\n'
    query_description += json.dumps(task_schema['input'], indent=2) + '\n\n'
    query_description += 'Output (i.e. what you have to provide to the machine):\n'
    query_description += json.dumps(task_schema['output'], indent=2) + '\n\n'
    query_description += 'JSON data of the task:\n\n'
    query_description += json.dumps(task_data, indent=2) + '\n\n'

    return query_description

NL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You act as an intermediary between a machine (which has a very specific input and output schema) and an agent (who uses natural language).' \
    'You will receive a task description (including a schema of the input and output that the machine uses) and the corresponding data. Call the \"send_query\" tool with a natural language message where you ask to perform the task according to the data.' \
    'Make sure to mention all the relevant information. ' \
    'Do not worry about managing communication, everything is already set up for you. Just focus on asking the right question.' \
    'The send_query tool will return the reply of the service.\n' \
    'Once you have enough information, call the \"deliverStructuredOutput\" tool with parameters according to the task\'s output schema. \n' \
    'Note: you can only call send_query {max_queries} time(s), so be efficient. Similarly, you cannot call deliverStructuredOutput multiple times, so make sure to deliver the right output the first time.' \
    'If there is an error and the machine\'s input/output schema specifies how to handle it, return the error in that format. Otherwise, call the "register_error" tool.'
    #'If the query fails, do not attempt to send another query.'

def parse_and_handle_query(query: str, callback: Callable[[str], Dict]) -> str:
    """Parses and processes a query by calling the given callback.

    Args:
        query (str): The query to be processed.
        callback (Callable[[str], Dict]): The function that processes the query.

    Returns:
        str: The response from the callback or error information.
    """
    try:
        response = callback(query)

        if response['status'] == 'success':
            return response['body']
        else:
            if response.get('message', '').lower() == 'protocol rejected':
                raise ProtocolRejectedError('Protocol was rejected by the service')
            return 'Error calling the tool: ' + response['message']
    except ProtocolRejectedError:
        raise
    except Exception as e:
        # import traceback
        # traceback.print_exc()
        return 'Error calling the tool: ' + str(e)

class Querier:
    """Handles querying external services based on protocol documents and task schemas."""

    def __init__(self, toolformer: Toolformer, max_queries: int = 5, max_messages: int = None, force_query: bool = True):
        """
        Initializes the Querier with the given toolformer and query/message limits.

        Args:
            toolformer (Toolformer): The Toolformer instance managing tools and conversations.
            max_queries (int, optional): Maximum number of queries allowed. Defaults to 5.
            max_messages (int, optional): Maximum number of messages allowed. If None, set to max_queries * 2. Defaults to None.
            force_query (bool, optional): Whether to enforce sending a query before output. Defaults to True.
        """
        self.toolformer = toolformer
        self.max_queries = max_queries

        if max_messages is None:
            max_messages = max_queries * 2

        self.max_messages = max_messages
        self.force_query = force_query

    def handle_conversation(
        self,
        prompt: str,
        message: str,
        output_schema: dict,
        callback: Callable[[str], Dict]
    ) -> str:
        """
        Manages the conversation flow for handling queries and delivering outputs.

        Args:
            prompt (str): The initial prompt for the conversation.
            message (str): The message to process in the conversation.
            output_schema (dict): The schema defining the structure of the expected output.
            callback (Callable[[str], Dict]): A callback function to handle query responses.

        Returns:
            str: The structured output produced by the conversation.
        """
        query_counter = 0

        def send_query_internal(query):
            # print('Sending query:', query)
            nonlocal query_counter
            query_counter += 1

            if query_counter > self.max_queries:
                # LLM is not listening, issue a warning
                return 'You have attempted to send too many queries. Finish the message and allow the user to speak, or the system will crash.'

            return parse_and_handle_query(query, callback)

        def send_query(query: str) -> str:
            """
            Send a query to the other service based on a protocol document.
            
            Args:
                query: The query to send to the service
            
            Returns:
                The response from the service
            """
            return send_query_internal(query)

        send_query_tool = Tool.from_function(send_query)

        found_output = None
        found_error = None

        def register_output(**kwargs) -> str:
            # print('Registering output:', kwargs)

            nonlocal found_output

            if self.force_query and query_counter == 0:
                return 'You must send a query before delivering the structured output.'

            if found_output is not None:
                return 'You have already registered an output. You cannot register another one.'

            found_output = kwargs
            return 'Done'

        register_output_tool = Tool('deliverStructuredOutput', 'Deliver the structured output to the machine.',
            output_schema, { "type": "string", "description": "The sytem response to the structured output." }
        , register_output)

        def register_error(error : str) -> str:
            """
            Return an error message to the machine.

            Args:
                error: The error message to return to the machine

            Returns:
                A message to the machine saying that an error has been registered.
            """

            nonlocal found_error
            found_error = error
            # We do not raise immediately because this would be caught by some models
            return 'Error registered. Finish the message and allow the user to speak.'

        error_tool = Tool.from_function(register_error)

        prompt = prompt.format(max_queries=self.max_queries)

        conversation = self.toolformer.new_conversation(prompt, [send_query_tool, register_output_tool, error_tool], category='conversation')

        for _ in range(self.max_messages):
            conversation(message, print_output=True)

            if found_error is not None:
                raise ExecutionError(found_error)

            if found_output is not None:
                break

            # If we haven't sent a query yet, we can't proceed
            if query_counter == 0 and self.force_query:
                message = 'You must send a query before delivering the structured output.'
            elif found_output is None:
                message = 'You must deliver the structured output.'

        return found_output
    
    def __call__(
        self,
        task_schema: TaskSchemaLike,
        task_data: Any,
        protocol_document: str,
        callback: Callable[[str], Dict]
    ) -> str:
        """
        Executes the querying process based on task schema and protocol document.

        Args:
            task_schema (TaskSchemaLike): The schema of the task to be performed.
            task_data (Any): The data associated with the task.
            protocol_document (str): The document defining the protocol for querying.
            callback: A callback function to handle query responses.

        Returns:
            str: The structured output resulting from the querying process.
        """
        query_description = construct_query_description(protocol_document, task_schema, task_data)
        task_schema = TaskSchema.from_taskschemalike(task_schema)
        output_schema = task_schema.output_schema

        if output_schema is None:
            raise ValueError('Task schema must have an output schema to deliver structured output.')
        
        if output_schema['type'] == 'object' and 'properties' in output_schema:
            object_output = True
        else:
            output_schema = {
                'type': 'object',
                'properties': {
                    'output': output_schema
                }
            }
            object_output = False

        result = self.handle_conversation(PROTOCOL_QUERIER_PROMPT, query_description, output_schema, callback)

        if object_output:
            return result

        return result['output']