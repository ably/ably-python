from __future__ import absolute_import

from ably.types.authoptions import AuthOptions
from ably.util.exceptions import AblyException


class Options(AuthOptions):
    def __init__(self, client_id=None, log_level=0, tls=True, host=None,
                 ws_host=None, port=0, tls_port=0, use_text_protocol=True,
                 queue_messages=False, recover=False, **kwargs):
        super(Options, self).__init__(**kwargs)

        # TODO check these defaults

        self.__client_id = client_id
        self.__log_level = log_level
        self.__tls = tls
        self.__host = host
        self.__ws_host = ws_host
        self.__port = port
        self.__tls_port = tls_port
        self.__use_text_protocol = use_text_protocol
        self.__queue_messages = queue_messages
        self.__recover = recover

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
        self.__recover = value
