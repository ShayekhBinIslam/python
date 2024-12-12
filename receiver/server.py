import uuid
from flask import Flask, request, jsonify

from receiver.core import Receiver
from threading import Timer


class ReceiverServer:
    def __init__(self, receiver : Receiver):
        self.receiver = receiver
        self.app = Flask(__name__)
        self.conversation_storage = {}

        @self.app.route('/', methods=['POST'])
        def main():
            try:
                data = request.json

                conversation = self.receiver.create_conversation(data['protocolHash'], data['protocolSources'])

                if data.get('multiround', False):
                    # Multiround mode; generate a unique ID for the conversation
                    conversation_id = str(uuid.uuid4())

                    self.conversation_storage[conversation_id] = conversation

                    response = {
                        'status': 'success',
                        'conversationId': conversation_id,
                        'body': conversation(data['body'])
                    }

                    # Automatically delete the conversation after 300 seconds
                    Timer(300, lambda: self.conversation_storage.pop(conversation_id, None)).start()
                else:
                    response = {
                        'status': 'success',
                        'body': conversation(data['body'])
                    }

                return jsonify(response)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                })
        
        @self.app.route('/conversations/<conversation_id>', methods=['POST', 'DELETE'])
        def continue_conversation(conversation_id):
            if request.method == 'DELETE':
                self.conversation_storage.pop(conversation_id, None)
                return jsonify({
                    'status': 'success'
                })
            
            data = request.json

            conversation = self.conversation_storage.get(conversation_id)

            if conversation is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Conversation not found.'
                })

            response = {
                'status': 'success',
                'body': conversation(data['body'])
            }

            return jsonify(response)

    def run(self, *args, **kwargs):
        self.app.run(*args, **kwargs)