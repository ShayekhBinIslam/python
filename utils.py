import base64
import hashlib
import requests
import urllib.parse

import yaml

def extract_substring(text : str, start_tag : str, end_tag : str):
    start_position = text.lower().find(start_tag.lower())
    end_position = text.lower().find(end_tag.lower(), start_position + len(start_tag))

    if start_position == -1 or end_position == -1:
        return None

    return text[start_position + len(start_tag):end_position].strip()

def send_raw_query(text, protocol_id, target_node, source, timeout=10000):
    from receiver.core_old import Receiver
    from receiver.storage import LocalReceiverStorage
    from toolformers.camel import CamelToolformer
    from camel.types import ModelPlatformType, ModelType
    from receiver.components.responder import Responder
    memory = LocalReceiverStorage()
    toolformer = CamelToolformer(ModelPlatformType.OPENAI, ModelType.GPT_4O, {})

    return Receiver(memory, Responder(toolformer, memory, [], ''), []).handle_query(protocol_id, [source], text)

def compute_hash(s):
    # Hash a string using SHA-1 and return the base64 encoded result

    m = hashlib.sha1()
    m.update(s.encode())

    b = m.digest()

    return base64.b64encode(b).decode('ascii')

def extract_metadata(text : str):
    metadata = extract_substring(text, '---', '---')

    print('Extracted metadata:', metadata)

    metadata = yaml.safe_load(metadata)

    name = metadata.get('name', 'Unnamed protocol')
    description = metadata.get('description', 'No description provided')
    multiround = metadata.get('multiround', False)
    
    return {
        'name': name,
        'description': description,
        'multiround': multiround
    }

def encode_as_data_uri(text):
    # Avoid base64, since it's expensive
    return 'data:text/plain;charset=utf-8,' + urllib.parse.quote(text)

def download_and_verify_protocol(protocol_hash, protocol_source, timeout=10000):
    if protocol_source.startswith('data:'):
        # Check if it's base64 encoded
        if protocol_source.startswith('data:text/plain;charset=utf-8;base64,'):
            protocol = base64.b64decode(protocol_source[len('data:text/plain;charset=utf-8;base64,'):]).decode('utf-8')
        elif protocol_source.startswith('data:text/plain;charset=utf-8,'):
            protocol = urllib.parse.unquote(protocol_source[len('data:text/plain;charset=utf-8,'):])
        else:
            print('Unsupported data URI:', protocol_source)
            return None
    else:
        response = requests.get(protocol_source, timeout=timeout)
        # It's just a simple txt file
        if response.status_code == 200:
            protocol = response.text
        else:
            print('Failed to download protocol from', protocol_source)
            return None

    # Check if the hash matches
    if compute_hash(protocol) == protocol_hash:
        return protocol

    print('Protocol does not match has:', protocol_source)
    return None
