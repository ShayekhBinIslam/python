import base64
import hashlib
import requests

def extract_substring(text, start_tag, end_tag):
    start_position = text.lower().find(start_tag.lower())
    end_position = text.lower().find(end_tag.lower())

    if start_position == -1 or end_position == -1:
        return None

    return text[start_position + len(start_tag):end_position].strip()

def send_raw_query(text, protocol_id, target_node, source, timeout=10000):
    from receiver.core import Receiver
    from receiver.storage import LocalReceiverStorage
    from toolformers.camel import CamelToolformer
    from camel.types import ModelPlatformType, ModelType
    from receiver.responder import Responder
    memory = LocalReceiverStorage()
    toolformer = CamelToolformer(ModelPlatformType.OPENAI, ModelType.GPT_4O, {})

    return Receiver(memory, Responder(toolformer, memory, [], ''), []).handle_query(protocol_id, [source], text)

    return requests.post(target_node, json={
        'protocolHash': protocol_id,
        'body': text,
        'protocolSources' : [source]
    }, timeout=timeout)

def compute_hash(s):
    # Hash a string using SHA-1 and return the base64 encoded result

    m = hashlib.sha1()
    m.update(s.encode())

    b = m.digest()

    return base64.b64encode(b).decode('ascii')

def download_and_verify_protocol(protocol_hash, protocol_source, timeout=10000):
    response = requests.get(protocol_source, timeout=timeout)
    # It's just a simple txt file
    if response.status_code == 200:
        protocol = response.text
        print('Protocol:', protocol)

        print('Found hash:', compute_hash(protocol))
        print('Target hash:', protocol_hash)
        # Check if the hash matches
        if compute_hash(protocol) == protocol_hash:
            print('Hashes match!')
            return protocol
    print('Failed to download protocol from', protocol_source)
    return None
