from __future__ import absolute_import

from ably.types.authoptions import AuthOptions

class Options(AuthOptions):
    def __init__(self, **kwargs):
        super(AuthOptions, self).__init__(self, **kwargs)

        # TODO check these defaults
        self.__client_id = None
        self.__log_level = 0
        self.__tls = True
        self.__host = None
        self.__ws_host = None
        self.__port = 0
        self.__tls_port = 0
        self.__use_text_protocol = False
        self.__queue_messages = False
        self.__recover = None

    @classmethod
    def with_key(cls, key):
        return cls(key=key)

    @property
    def client_id(self):
        return self.__client_id

    @client_id.setter
    def client_id(self, value):
        self.__client_id = value

    @property
    def log_level(self):
        return self.__log_level

    @log_level.setter
    def log_level(self, value):
        self.__log_level = value

    @property
    def tls(self):
        return self.__tls

    @tls.setter
    def tls(self, value):
        self.__tls = value

    @property
    def host(self):
        return self.__host

    @host.setter
    def host(self, value):
        self.__host = value

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, value):
        self.__port = value

    @property
    def tls_port(self):
        return self.__tls_port

    @tls_port.setter
    def tls_port(self, value):
        self.__tls_port = value

    @property
    def use_text_protocol(self):
        return self.__use_text_protocol

    @use_text_protocol.setter
    def use_text_protocol(self, value):
        self.__use_text_protocol = value

    @property
    def queue_messages(self):
        return self.__queue_messages

    @queue_messages.setter
    def queue_messages(self, value):
        self.__queue_messages = value

    @property
    def recover(self):
        return self.__recover

    @recover.setter
    def recover(self, value):
        self.__recover = recover
