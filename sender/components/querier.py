# The querier queries a service based on a protocol document.
# It receives the protocol document and writes the query that must be performed to the system.

import json
import os
from pathlib import Path

import sys

from toolformers.base import Tool, StringParameter, parameter_from_openai_api

from utils import send_raw_query

PROTOCOL_QUERIER_PROMPT = 'You are QuerierGPT. You will receive a protocol document detailing how to query a service. Reply with a structured query which can be sent to the service.' \
    'Only reply with the query itself, with no additional information or escaping. Similarly, do not add any additional whitespace or formatting.'

def construct_query_description(protocol_document, task_schema, task_data):
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

NL_QUERIER_PROMPT = 'You are NaturalLanguageQuerierGPT. You act as an intermediary between a machine (who has a very specific input and output schema) and an agent (who uses natural language).' \
    'You will receive a task description (including a schema of the input and output) that the machine uses and the corresponding data. Call the \"sendQuery\" tool with a natural language message where you ask to perform the task according to the data.' \
    'Make sure to mention all the relevant information. ' \
    'Do not worry about managing communication, everything is already set up for you. Just focus on asking the right question.' \
    'The sendQuery tool will return the reply of the service.\n' \
    'Once you receive the reply, call the \"deliverStructuredOutput\" tool with parameters according to the task\'s output schema. \n' \
    'Note: you cannot call sendQuery multiple times, so make sure to ask the right question the first time. Similarly, you cannot call deliverStructuredOutput multiple times, so make sure to deliver the right output the first time.' \
    'If the query fails, do not attempt to send another query.'

def parse_and_handle_query(query, callback):
    # TODO: Replace with transporter
    try:
        response = callback(query)

        if response['status'] == 'success':
            return response['body']
        else:
            return 'Error calling the tool: ' + response['message']
    except Exception as e:
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
    def __init__(self, toolformer):
        self.toolformer = toolformer

    def handle_conversation(self, prompt, message, output_parameters, callback):
        sent_query_counter = 0
        
        def send_query_internal(query):
            print('Sending query:', query)
            nonlocal sent_query_counter
            sent_query_counter += 1

            if sent_query_counter > 50:
                # All hope is lost, crash
                sys.exit(-2)
            elif sent_query_counter > 10:
                # LLM is not listening, throw an exception
                raise Exception('Too many attempts to send queries. Exiting.')
            elif sent_query_counter > 5:
                # LLM is not listening, issue a warning
                return 'You have attempted to send too many queries. Finish the message and allow the user to speak, or the system will crash.'
            elif sent_query_counter > 1:
                return 'You have already sent a query. You cannot send another one.'
            return parse_and_handle_query(query, callback)

        send_query_tool = Tool('sendQuery', 'Send a query to the other service based on a protocol document.', [
            StringParameter('query', 'The query to send to the service', True)
        ], send_query_internal)

        found_output = None
        registered_output_counter = 0

        def register_output(**kwargs):
            print('Registering output:', kwargs)

            nonlocal found_output
            nonlocal registered_output_counter
            if found_output is not None:
                registered_output_counter += 1

            if registered_output_counter > 50:
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

        conversation = self.toolformer.new_conversation(prompt, [send_query_tool, register_output_tool], category='conversation')

        for i in range(5):
            conversation(message, print_output=True)

            if found_output is not None:
                break

            # If we haven't sent a query yet, we can't proceed
            if sent_query_counter == 0:
                message = 'You must send a query before delivering the structured output.'
            elif found_output is None:
                message = 'You must deliver the structured output.'

        return found_output
    
    def __call__(self, task_schema, task_data, protocol_document, callback):
        query_description = construct_query_description(protocol_document, task_schema, task_data)
        output_parameters = get_output_parameters(task_schema)

        return self.handle_conversation(PROTOCOL_QUERIER_PROMPT, query_description, output_parameters, callback)


    #def send_query_with_protocol(self, storage, task_schema, task_data, target_node, protocol_id, source):
    #    base_folder = Path(os.environ.get('STORAGE_PATH')) / 'protocol_documents'
    #    protocol_document = storage.load_protocol_document(base_folder, protocol_id)
    #    query_description = construct_query_description(protocol_document, task_schema, task_data)
    #    output_parameters = get_output_parameters(task_schema)
#
    #    return self.handle_conversation(PROTOCOL_QUERIER_PROMPT, query_description, target_node, protocol_id, source, output_parameters)
#
    #def send_query_without_protocol(self, task_schema, task_data, target_node):
    #    query_description = construct_query_description(None, task_schema, task_data)
    #    output_parameters = get_output_parameters(task_schema)
#
    #    return self.handle_conversation(NL_QUERIER_PROMPT, query_description, target_node, None, None, output_parameters)
    #
    #def send_query(self, storage, task_schema, task_data, target_node, protocol_id, source):
    #    if protocol_id is not None:
    #        return self.send_query_with_protocol(storage, task_schema, task_data, target_node, protocol_id, source)
    #    else:
    #        return self.send_query_without_protocol(task_schema, task_data, target_node)
