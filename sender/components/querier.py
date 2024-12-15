# The querier queries a service based on a protocol document.
# It receives the protocol document and writes the query that must be performed to the system.

import json
import sys
from typing import Callable, Dict

from toolformers.base import Tool, Toolformer, StringParameter, parameter_from_openai_api

PROTOCOL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You act as an intermediary between a machine (who has a very specific input and output schema) and an external service (which follows a very specific protocol).' \
    'You will receive a task description (including a schema of the input and output that the machine uses) and the corresponding data. Call the \"sendQuery\" tool with a message following the protocol.' \
    'Do not worry about managing communication, everything is already set up for you. Just focus on sending the right message.' \
    'The sendQuery tool will return the reply of the service.\n' \
    'Some protocols may explictly require multiple queries. In that case, you can call sendQuery multiple times. Otherwise, call it only once. \n' \
    'In any case, you cannot call sendQuery more than {max_queries} time(s), no matter what the protocol says.' \
    'Once you receive the reply, call the "deliverStructuredOutput" tool with parameters according to the task\'s output schema. \n' \
    'You cannot call deliverStructuredOutput multiple times, so make sure to deliver the right output the first time.' \
    'If there is an error and the machine\'s input/output schema specifies how to handle an error, return the error in that format. Otherwise, call the "error" tool.' \
    #'Also, if the query fails to .'

def construct_query_description(protocol_document : str, task_schema, task_data):
    query_description = ''
    if protocol_document is not None:
        query_description += 'Protocol document:\n\n'
        query_description += protocol_document + '\n\n'
    query_description += 'JSON schema of the task:\n\n'
    query_description += 'Input (i.e. what the machine will provide you):\n'
    query_description += json.dumps(task_schema['input'], indent=2) + '\n\n'
    query_description += 'Output (i.e. what you have to provide to the machine):\n'
    query_description += json.dumps(task_schema['output'], indent=2) + '\n\n'
    query_description += 'JSON data of the task:\n\n'
    query_description += json.dumps(task_data, indent=2) + '\n\n'

    return query_description

NL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You act as an intermediary between a machine (which has a very specific input and output schema) and an agent (who uses natural language).' \
    'You will receive a task description (including a schema of the input and output that the machine uses) and the corresponding data. Call the \"sendQuery\" tool with a natural language message where you ask to perform the task according to the data.' \
    'Make sure to mention all the relevant information. ' \
    'Do not worry about managing communication, everything is already set up for you. Just focus on asking the right question.' \
    'The sendQuery tool will return the reply of the service.\n' \
    'Once you have enough information, call the \"deliverStructuredOutput\" tool with parameters according to the task\'s output schema. \n' \
    'Note: you can only call sendQuery {max_queries} time(s), so be efficient. Similarly, you cannot call deliverStructuredOutput multiple times, so make sure to deliver the right output the first time.' \
    'If there is an error and the machine\'s input/output schema specifies how to handle it, return the error in that format. Otherwise, call the "error" tool.'
    #'If the query fails, do not attempt to send another query.'

def parse_and_handle_query(query, callback : Callable[[str], Dict]):
    try:
        response = callback(query)

        if response['status'] == 'success':
            return response['body']
        else:
            return 'Error calling the tool: ' + response['message']
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 'Error calling the tool: ' + str(e)

def get_output_parameters(task_schema):
    output_schema = task_schema['output']
    required_parameters = output_schema['required']

    parameters = []

    for parameter_name, parameter_schema in output_schema['properties'].items():
        parameter = parameter_from_openai_api(parameter_name, parameter_schema, parameter_name in required_parameters)
        parameters.append(parameter)
    
    return parameters

class Querier:
    def __init__(self, toolformer : Toolformer, max_queries : int = 5, max_messages : int = None):
        self.toolformer = toolformer
        self.max_queries = max_queries

        if max_messages is None:
            max_messages = max_queries * 2

        self.max_messages = max_messages

    def handle_conversation(self, prompt : str, message : str, output_parameters, callback):
        query_counter = 0

        def send_query_internal(query):
            print('Sending query:', query)
            nonlocal query_counter
            query_counter += 1

            if query_counter > self.max_queries + 10:
                # All hope is lost, crash
                sys.exit(-2)
            elif query_counter > self.max_queries + 5:
                # LLM is not listening, throw an exception
                raise Exception('Too many attempts to send queries. Exiting.')
            elif query_counter > self.max_queries:
                # LLM is not listening, issue a warning
                return 'You have attempted to send too many queries. Finish the message and allow the user to speak, or the system will crash.'

            return parse_and_handle_query(query, callback)

        send_query_tool = Tool('sendQuery', 'Send a query to the other service based on a protocol document.', [
            StringParameter('query', 'The query to send to the service', True)
        ], send_query_internal)

        found_output = None
        found_error = None
        registered_output_counter = 0

        def register_output(**kwargs):
            print('Registering output:', kwargs)

            nonlocal found_output
            nonlocal registered_output_counter
            if found_output is not None:
                registered_output_counter += 1

            if registered_output_counter > 20:
                # All hope is lost, crash
                sys.exit(-2)
            elif registered_output_counter > 10:
                # LLM is not listening, raise an exception
                raise Exception('Too many attempts to register outputs. Exiting.')
            elif registered_output_counter > 5:
                # LLM is not listening, issue a warning
                return 'You have attempted to register too many outputs. Finish the message and allow the user to speak, or the system will crash.'
            elif registered_output_counter > 0:
                return 'You have already registered an output. You cannot register another one.'

            output = json.dumps(kwargs)

            found_output = output
            return 'Done'

        register_output_tool = Tool('deliverStructuredOutput', 'Deliver the structured output to the machine.',
            output_parameters
        , register_output)

        def register_error(error):
            nonlocal found_error
            found_error = error
            return 'Error registered. Finish the message and allow the user to speak.'

        error_tool = Tool('error', 'Return an error message to the machine.', [
            StringParameter('error', 'The error message to return to the machine', True)
        ], register_error)

        prompt = prompt.format(max_queries=self.max_queries)

        conversation = self.toolformer.new_conversation(prompt, [send_query_tool, register_output_tool, error_tool], category='conversation')

        # TODO: Make number of attempts configurable
        for _ in range(self.max_messages):
            conversation(message, print_output=True)

            if found_error is not None:
                raise Exception('Error:', found_error)

            if found_output is not None:
                break

            # If we haven't sent a query yet, we can't proceed
            if query_counter == 0:
                message = 'You must send a query before delivering the structured output.'
            elif found_output is None:
                message = 'You must deliver the structured output.'

        return found_output
    
    def __call__(self, task_schema, task_data, protocol_document, callback):
        query_description = construct_query_description(protocol_document, task_schema, task_data)
        output_parameters = get_output_parameters(task_schema)

        return self.handle_conversation(PROTOCOL_QUERIER_PROMPT, query_description, output_parameters, callback)
