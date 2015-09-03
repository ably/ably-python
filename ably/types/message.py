from __future__ import absolute_import

import base64
import json
import logging
import time

import six
import msgpack

from ably.types.typedbuffer import TypedBuffer
from ably.types.mixins import EncodeDataMixin
from ably.util.crypto import CipherData
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


class Message(EncodeDataMixin):
    def __init__(self, name=None, data=None, client_id=None,
                 id=None, connection_id=None, timestamp=None,
                 encoding=''):
        if name is None:
            self.__name = None
        elif isinstance(name, six.string_types):
            self.__name = name
        elif isinstance(name, six.binary_type):
            self.__name = name.decode('ascii')
        else:
            # log.debug(name)
            # log.debug(name.__class__)
            raise ValueError("name must be a string or bytes")
        self.__id = id
        self.__client_id = client_id
        self.__data = data
        self.__timestamp = timestamp
        self.__connection_id = connection_id
        super(Message, self).__init__(encoding)

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
    def client_id(self):
        return self.__client_id

    @property
    def data(self):
        return self.__data

    @property
    def connection_id(self):
        return self.__connection_id

    @property
    def id(self):
        return self.__id

    @property
    def timestamp(self):
        return self.__timestamp

    def encrypt(self, channel_cipher):
        if isinstance(self.data, CipherData):
            return

        elif isinstance(self.data, six.text_type):
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

    def as_dict(self):
        data = self.data
        data_type = None
        encoding = self._encoding_array[:]
        if isinstance(data, dict) or isinstance(data, list):
            encoding.append('json')
            data = json.dumps(data)

        elif isinstance(self.data, six.binary_type):
            data = base64.b64encode(data).decode('ascii')
            encoding.append('base64')

        elif isinstance(data, six.text_type):
            encoding.append('utf-8')

        elif isinstance(data, CipherData):
            encoding.append(data.encoding_str)
            data_type = data.type
            data = base64.b64encode(data.buffer).decode('ascii')
            encoding.append('base64')

        if not (isinstance(data, (six.binary_type, six.text_type, list, dict)) or
                data is None):
            raise AblyException("Invalid data payload", 400, 40011)

        request_body = {
            'name': self.name,
            'data': data,
            'timestamp': self.timestamp or int(time.time() * 1000.0),
        }
        request_body = {k: v for (k, v) in request_body.items()
                        if v is not None}  # None values aren't included

        if encoding:
            request_body['encoding'] = '/'.join(encoding).strip('/')

        if data_type:
            request_body['type'] = data_type

        if self.client_id:
            request_body['clientId'] = self.client_id

        if self.id:
            request_body['id'] = self.id

        if self.connection_id:
            request_body['connectionId'] = self.connection_id

        return request_body

    def as_json(self):
        return json.dumps(self.as_dict(), separators=(',', ':'))

    @staticmethod
    def from_json(obj, cipher=None):
        id = obj.get('id')
        name = obj.get('name')
        data = obj.get('data')
        client_id = obj.get('clientId')
        connection_id = obj.get('connectionId')
        timestamp = obj.get('timestamp')
        encoding = obj.get('encoding', '')

        decoded_data = Message.decode(data, encoding, cipher)

        return Message(
            id=id,
            name=name,
            connection_id=connection_id,
            client_id=client_id,
            timestamp=timestamp,
            **decoded_data
        )

    def as_msgpack(self):
        data = self.data
        encoding = None
        data_type = None

        # log.debug(data.__class__)

        if isinstance(data, CipherData):
            data_type = data.type
            data = base64.b64encode(data.buffer).decode('ascii')
            encoding = 'cipher+base64'
        if isinstance(data, six.binary_type):
            data = base64.b64encode(data).decode('ascii')
            encoding = 'base64'

        # log.debug(data)
        # log.debug(data.__class__)

        request_body = {
            'name': self.name,
            'data': data,
            'timestamp': self.timestamp or int(time.time() * 1000.0),
        }

        if encoding:
            request_body['encoding'] = encoding

        if data_type:
            request_body['type'] = data_type

        request_body = json.dumps(request_body)
        return request_body

    @staticmethod
    def from_msgpack(obj):
        name = obj.get('name')
        data = obj.get('data')
        timestamp = obj.get('timestamp')
        encoding = obj.get('encoding')

        # log.debug("MESSAGE: %s", str(obj))

        if encoding and encoding == six.u('base64'):
            data = msgpack.loads(base64.b64decode(data))
        elif encoding and encoding == six.u('cipher+base64'):
            ciphertext = base64.b64decode(data)
            data = CipherData(ciphertext, obj.get('type'))
            data = msgpack.loads(data)

        return Message(name=name, data=data, timestamp=timestamp)


def message_response_handler(response):
    return [Message.from_json(j) for j in response.json()]


def make_encrypted_message_response_handler(cipher):
    def encrypted_message_response_handler(response):
        return [Message.from_json(j, cipher) for j in response.json()]
    return encrypted_message_response_handler


class MessageJSONEncoder(json.JSONEncoder):
    def default(self, message):
        if isinstance(message, Message):
            return message.as_dict()
        else:
            return json.JSONEncoder.default(self, message)
