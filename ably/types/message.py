import base64
import json
import logging

from ably.types.typedbuffer import TypedBuffer
from ably.types.mixins import EncodeDataMixin
from ably.util.crypto import CipherData
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


def to_text(value):
    if value is None:
        return value
    elif isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        return value.decode()
    else:
        raise TypeError("expected string or bytes, not %s" % type(value))


class Message(EncodeDataMixin):

    def __init__(self,
                 name=None,  # TM2g
                 data=None,  # TM2d
                 client_id=None,  # TM2b
                 id=None,  # TM2a
                 connection_id=None,  # TM2c
                 connection_key=None,  # TM2h
                 encoding='',  # TM2e
                 timestamp=None,  # TM2f
                 extras=None,  # TM2i
                 ):

        super().__init__(encoding)

        self.__name = to_text(name)
        self.__data = data
        self.__client_id = to_text(client_id)
        self.__id = to_text(id)
        self.__connection_id = connection_id
        self.__connection_key = connection_key
        self.__timestamp = timestamp
        self.__extras = extras

    def __eq__(self, other):
        if isinstance(other, Message):
            return (self.name == other.name
                    and self.data == other.data
                    and self.client_id == other.client_id
                    and self.timestamp == other.timestamp)
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Message):
            result = self.__eq__(other)
            if result != NotImplemented:
                return not result
        return NotImplemented

    @property
    def name(self):
        return self.__name

    @property
    def data(self):
        return self.__data

    @property
    def client_id(self):
        return self.__client_id

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        self.__id = value

    @property
    def connection_id(self):
        return self.__connection_id

    @property
    def connection_key(self):
        return self.__connection_key

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def extras(self):
        return self.__extras

    def encrypt(self, channel_cipher):
        if isinstance(self.data, CipherData):
            return

        elif isinstance(self.data, str):
            self._encoding_array.append('utf-8')

        if isinstance(self.data, dict) or isinstance(self.data, list):
            self._encoding_array.append('json')
            self._encoding_array.append('utf-8')

        typed_data = TypedBuffer.from_obj(self.data)
        if typed_data.buffer is None:
            return True
        encrypted_data = channel_cipher.encrypt(typed_data.buffer)
        self.__data = CipherData(encrypted_data, typed_data.type,
                                 cipher_type=channel_cipher.cipher_type)

    @staticmethod
    def decrypt_data(channel_cipher, data):
        if not isinstance(data, CipherData):
            return
        decrypted_data = channel_cipher.decrypt(data.buffer)
        decrypted_typed_buffer = TypedBuffer(decrypted_data, data.type)

        return decrypted_typed_buffer.decode()

    def decrypt(self, channel_cipher):
        decrypted_data = self.decrypt_data(channel_cipher, self.__data)
        if decrypted_data is not None:
            self.__data = decrypted_data

    def as_dict(self, binary=False):
        data = self.data
        data_type = None
        encoding = self._encoding_array[:]

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
            data_type = data.type
            if not binary:
                data = base64.b64encode(data.buffer).decode('ascii')
                encoding.append('base64')
            else:
                data = data.buffer
        elif binary and isinstance(data, bytearray):
            data = bytes(data)

        if not (isinstance(data, (bytes, str, list, dict, bytearray)) or data is None):
            raise AblyException("Invalid data payload", 400, 40011)

        request_body = {
            'name': self.name,
            'data': data,
            'timestamp': self.timestamp or None,
            'type': data_type or None,
            'clientId': self.client_id or None,
            'id': self.id or None,
            'connectionId': self.connection_id or None,
            'connectionKey': self.connection_key or None,
            'extras': self.extras,
        }

        if encoding:
            request_body['encoding'] = '/'.join(encoding).strip('/')

        # None values aren't included
        request_body = {k: v for k, v in request_body.items() if v is not None}

        return request_body

    @staticmethod
    def from_encoded(obj, cipher=None):
        id = obj.get('id')
        name = obj.get('name')
        data = obj.get('data')
        client_id = obj.get('clientId')
        connection_id = obj.get('connectionId')
        timestamp = obj.get('timestamp')
        encoding = obj.get('encoding', '')
        extras = obj.get('extras', None)

        decoded_data = Message.decode(data, encoding, cipher)

        return Message(
            id=id,
            name=name,
            connection_id=connection_id,
            client_id=client_id,
            timestamp=timestamp,
            extras=extras,
            **decoded_data
        )


def make_message_response_handler(cipher):
    def encrypted_message_response_handler(response):
        messages = response.to_native()
        return Message.from_encoded_array(messages, cipher=cipher)
    return encrypted_message_response_handler
