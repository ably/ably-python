import base64
import json
from typing import Any

from ably.util.crypto import CipherData


def encode_data(data: Any, encoding_array: list, binary: bool = False):
    encoding = encoding_array[:]

    if isinstance(data, (dict, list)):
        encoding.append('json')
        data = json.dumps(data)
        data = str(data)
    elif isinstance(data, str) and not binary:
        pass
    elif not binary and isinstance(data, (bytearray, bytes)):
        data = base64.b64encode(data).decode('ascii')
        encoding.append('base64')
    elif isinstance(data, CipherData):
        encoding.append(data.encoding_str)
        if not binary:
            data = base64.b64encode(data.buffer).decode('ascii')
            encoding.append('base64')
        else:
            data = data.buffer
    elif binary and isinstance(data, bytearray):
        data = bytes(data)

    return {
        'data': data,
        'encoding': '/'.join(encoding).strip('/')
    }
