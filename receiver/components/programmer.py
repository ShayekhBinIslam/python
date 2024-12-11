from typing import List

from toolformers.base import Tool, Toolformer
from utils import extract_substring

TOOL_PROGRAMMER_PROMPT = '''
You are ProtocolProgrammerGPT. Your task is to write a routine that takes a query formatted according to the protocol and returns a response.
The routine is a Python file that contains a function "reply". reply takes a single argument, "query", which is a string, and must return a string.
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

def reply(query):
  ...

</IMPLEMENTATION>
'''

class ReceiverProgrammer:
    def __init__(self, toolformer : Toolformer, num_attempts : int = 5):
        self.toolformer = toolformer
        self.num_attempts = num_attempts

    def __call__(self, tools : List[Tool], protocol_document : str, additional_info : str = ''):
        message = 'Protocol document:\n\n' + protocol_document + '\n\n' + 'Additional functions:\n\n'

        if len(tools) == 0:
            message += 'No additional functions provided'
        else:
            for tool in tools:
                message += tool.as_documented_python() + '\n\n'

        conversation = self.toolformer.new_conversation(TOOL_PROGRAMMER_PROMPT + additional_info, [], category='programming')

        for _ in range(self.num_attempts):
            reply = conversation.chat(message, print_output=True)

            implementation = extract_substring(reply, '<IMPLEMENTATION>', '</IMPLEMENTATION>')

            if implementation is not None:
                break

            message = 'You have not provided an implementation yet. Please provide one by surrounding it in the tags <IMPLEMENTATION> and </IMPLEMENTATION>.'

        implementation = implementation.strip()

        # Sometimes the LLM leaves the Markdown formatting in the implementation
        implementation = implementation.replace('```python', '').replace('```', '').strip()

        implementation = implementation.replace('def reply(', 'def run(')

        return implementation