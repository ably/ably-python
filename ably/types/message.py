from __future__ import absolute_import

from ably.types.typedbuffer import TypedBuffer
from ably.util.crypto import CipherData

class Message(object):
    def __init__(self, name=None, data=None, client_id=None):
        self.__name = name
        self.__client_id = client_id
        self.__data = data

    @property
    def name(self):
        return self.__name

    @property
    def client_id(self):
        return self.__client_id

    @property
    def data(self):
        return self.__data

    def encrypt(self, channel_cipher):
        if isinstance(self.data, CipherData):
            return

        typed_data = TypedBuffer.from_obj(self.data)
        encrypted_data = channel_cipher.encrypt(typed_data.buffer)

        self.data = CipherData(encrypted_data, typed_data.type)

    def decrypt(self, channel_cipher):
        if not isinstance(self.data, CipherData):
            return

        decrypted_data = channel_cipher.decrypt(self.data.buffer)
        decrypted_typed_buffer = TypedBuffer(decrypted_data, self.data.type)

        self.data = decrypted_typed_buffer.decode()
