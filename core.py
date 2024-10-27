from typing import Callable, Optional

import requests

def send_query(hash : Optional[str], query : str, url : str) -> str:
    res = requests.post(url, json={
        'protocolHash': hash,
        'body': query
    })

    if res.status_code != 200:
        raise Exception(f"Failed to send query: {res.text}")
    
    parsed = res.json()
    if parsed['status'] != 'success':
        raise Exception(f"Failed to send query: {parsed['error']}")

    return parsed['body']

# Takes a hash and a query, returns the result
DemultiplexFunction = Callable[[str, dict], str]

def handle_query(structured_query : dict, demultiplexer : DemultiplexFunction) -> dict:
    protocol_hash = structured_query.get('protocolHash', None)
    query = structured_query['body']
    try:
        result = demultiplexer(protocol_hash, query)

        return {
            'status': 'success',
            'body': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
