from __future__ import absolute_import

from ably.types.capability import Capability


class TokenParams(object):
    def __init__(self, id=None, ttl=0, capability=None, client_id=None,
            timestamp=None, nonce=None, mac=None):
        self.__id = id
        self.__ttl = ttl
        self.__capability = Capability(capability or {})
        self.__client_id = client_id
        self.__timestamp = timestamp
        self.__nonce = nonce
        self.__mac = mac

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        self.__id = value

    @property
    def ttl(self):
        return self.__ttl

    @ttl.setter
    def ttl(self, value):
        self.__ttl = value

    @property
    def capability(self):
        return self.__capability

    @capability.setter
    def capability(self, value):
        self.__capability = value

    @property
    def client_id(self):
        return self.__client_id

    @client_id.setter
    def client_id(self, value):
        self.__client_id = value

    @property
    def timestamp(self):
        return self.__timestamp

    @timestamp.setter
    def timestamp(self, value):
        self.__timestamp = value

    @property
    def nonce(self):
        return self.__nonce

    @nonce.setter
    def nonce(self, value):
        self.__nonce = value

    @property
    def mac(self):
        return self.__mac

    @mac.setter
    def mac(self, value):
        self.__mac = value
