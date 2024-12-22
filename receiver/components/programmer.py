from typing import List

from common.toolformers.base import Tool, ToolLike, Toolformer
from utils import extract_substring

NO_MULTIROUND_REPLY = ''' reply takes a single argument, "query", which is a string, and must return a string.
'''

MULTIROUND_REPLY = '''reply takes two arguments:
- "query", which is a string
- "memory", which is a dictionary that can be used to store information between rounds (if the protocol requires the receiver to act in multiple rounds).
It must return a tuple of two elements:
- A string, which is the response to the query
- A dictionary, which is the updated memory
'''

NO_MULTIROUND_EXAMPLE = '''
def reply(query):
    ...
    return response
'''

MULTIROUND_EXAMPLE = '''
def reply(query, memory):
    ...
    return response, updated_memory
'''

TOOL_PROGRAMMER_PROMPT = '''
You are ProtocolProgrammerGPT. Your task is to write a routine that takes a query formatted according to the protocol and returns a response.
The routine is a Python file that contains a function "reply". {reply_description}
Depending on the protocol, the routine might be need to perform some actions before returning the response. The user might provide you with a list of \
Python functions you can call to help you with this task. You don't need to worry about importing them, they are already available in the environment.
Rules:
- The implementation must be written in Python.
- You can define any number of helper functions and import any libraries that are part of the Python standard library.
- Do not import libraries that are not part of the Python standard library.
- Remember to import standard libraries if you need them.
- If there is an unexpected error that is not covered by the protocol, throw an exception.\
 If instead the protocol specifies how to handle the error, return the response according to the protocol's specification.
- Do not execute anything (aside from library imports) when the file itself is loaded. I will personally import the file and call the reply function with the task data.
Begin by thinking about the implementation and how you would structure the code. \
Then, write your implementation by writing a code block that contains the tags <IMPLEMENTATION> and </IMPLEMENTATION>. For example:
```python
<IMPLEMENTATION>
{example}

</IMPLEMENTATION>
'''

class ReceiverProgrammer:
    def __init__(self, toolformer : Toolformer, num_attempts : int = 5):
        self.toolformer = toolformer
        self.num_attempts = num_attempts

    def __call__(self, tools : List[ToolLike], protocol_document : str, multiround : bool, additional_info : str = ''):
        message = 'Protocol document:\n\n' + protocol_document + '\n\n' + 'Additional functions:\n\n'

        if len(tools) == 0:
            message += 'No additional functions provided'
        else:
            for tool in tools:
                tool = Tool.from_toollike(tool)
                message += str(tool) + '\n\n'

        prompt = TOOL_PROGRAMMER_PROMPT.format(
            reply_description=MULTIROUND_REPLY if multiround else NO_MULTIROUND_REPLY,
            example=MULTIROUND_EXAMPLE if multiround else NO_MULTIROUND_EXAMPLE
        )

        if additional_info:
            prompt += '\n\n' + additional_info

        conversation = self.toolformer.new_conversation(prompt, [], category='programming')

        for _ in range(self.num_attempts):
            reply = conversation(message, print_output=True)

            implementation = extract_substring(reply, '<IMPLEMENTATION>', '</IMPLEMENTATION>')

            if implementation is not None:
                break

            message = 'You have not provided an implementation yet. Please provide one by surrounding it in the tags <IMPLEMENTATION> and </IMPLEMENTATION>.'

        implementation = implementation.strip()

        # Sometimes the LLM leaves the Markdown formatting in the implementation
        implementation = implementation.replace('```python', '').replace('```', '').strip()

        implementation = implementation.replace('def reply(', 'def run(')

        return implementation