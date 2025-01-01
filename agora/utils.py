import base64
import hashlib
import requests
import urllib.parse

import yaml
from typing import Optional

def extract_substring(text: str, start_tag: str, end_tag: str) -> Optional[str]:
    """Extracts a substring from the given text, bounded by start_tag and end_tag.

    Args:
        text (str): The source string.
        start_tag (str): The beginning delimiter.
        end_tag (str): The ending delimiter.

    Returns:
        Optional[str]: The extracted substring or None if not found.
    """
    start_position = text.lower().find(start_tag.lower())
    end_position = text.lower().find(end_tag.lower(), start_position + len(start_tag))

    if start_position == -1 or end_position == -1:
        return None

    return text[start_position + len(start_tag):end_position].strip()

def compute_hash(s: str) -> str:
    """Computes a hash of the given string.

    Args:
        s (str): The input string to hash.

    Returns:
        str: The resulting hash as a Base64-encoded string.
    """
    m = hashlib.sha1()
    m.update(s.encode())

    b = m.digest()

    return base64.b64encode(b).decode('ascii')

def extract_metadata(text: str) -> dict:
    """Extracts metadata from the given text in YAML format.

    Args:
        text (str): The source text containing YAML metadata.

    Returns:
        dict: A dictionary of extracted metadata.
    """
    metadata = extract_substring(text, '---', '---')

    metadata = yaml.safe_load(metadata)

    name = metadata.get('name', 'Unnamed protocol')
    description = metadata.get('description', 'No description provided')
    multiround = metadata.get('multiround', False)
    
    return {
        'name': name,
        'description': description,
        'multiround': multiround
    }

def encode_as_data_uri(text: str) -> str:
    """Encodes the given text as a data URI.

    Args:
        text (str): The text to encode.

    Returns:
        str: The encoded data URI.
    """
    return 'data:text/plain;charset=utf-8,' + urllib.parse.quote(text)

def download_and_verify_protocol(protocol_hash: str, protocol_source: str, timeout: int = 10000) -> Optional[str]:
    """Downloads a protocol from a source or decodes it if it's a data URI, then verifies its hash.

    Args:
        protocol_hash (str): The expected hash of the protocol.
        protocol_source (str): The protocol's location (URL or data URI).
        timeout (int): The request timeout in milliseconds.

    Returns:
        Optional[str]: The protocol text if hash verification passes, otherwise None.
    """
    if protocol_source.startswith('data:'):
        # Check if it's base64 encoded
        if protocol_source.startswith('data:text/plain;charset=utf-8;base64,'):
            protocol = base64.b64decode(protocol_source[len('data:text/plain;charset=utf-8;base64,'):]).decode('utf-8')
        elif protocol_source.startswith('data:text/plain;charset=utf-8,'):
            protocol = urllib.parse.unquote(protocol_source[len('data:text/plain;charset=utf-8,'):])
        else:
            # print('Unsupported data URI:', protocol_source)
            return None
    else:
        response = requests.get(protocol_source, timeout=timeout)
        # It's just a simple txt file
        if response.status_code == 200:
            protocol = response.text
        else:
            # print('Failed to download protocol from', protocol_source)
            return None

    # Check if the hash matches
    if compute_hash(protocol) == protocol_hash:
        return protocol

    # print('Protocol does not match hash:', protocol_source)
    return None
