from __future__ import absolute_import

from ably.types.authoptions import AuthOptions
from ably.util.exceptions import AblyException


class Options(AuthOptions):
    def __init__(self, clientId=None, keyId=None, keyValue=None,log_level=0, tls=True, restHost=None,
                 ws_host=None, port=0, tls_port=0, use_text_protocol=True,
                 queue_messages=False, recover=False, useTokenAuth=False, authUrl=None, authCb=None, environment=None,**kwargs):
        super(Options, self).__init__(**kwargs)

        # TODO check these defaults


        self.__clientId = clientId
        self.__log_level = log_level
        self.__tls = tls
        self.__restHost = restHost
            
        self.__ws_host = ws_host
        self.__port = port
        self.__tls_port = tls_port
        self.__use_text_protocol = use_text_protocol
        self.__queue_messages = queue_messages
        self.__recover = recover
        self.__useTokenAuth = useTokenAuth
        self.__authUrl = authUrl
        self.__authCb = authCb
        self.__keyId = keyId
        self.__keyValue = keyValue
        self.__environment = environment

    @classmethod
    def with_key(cls, key, **kwargs):
        kwargs = kwargs or {}

        key_components = key.split(':')

        if len(key_components) != 2:
            raise AblyException("key of not len 2 parameters: {0}"
                                .format(key.split(':')),
                                401, 40101)

        kwargs['keyId'] = key_components[0]
        kwargs['keyValue'] = key_components[1]

        return cls(**kwargs)


    @property
    def environment(self):
        return self.__environment

    @environment.setter
    def environment(self, value):
        self.__environment = value
    
    @property
    def keyId(self):
        return self.__keyId
    @property
    def keyValue(self):
        return self.__keyValue
    
    @property
    def useTokenAuth(self):
        return self.__useTokenAuth

    @property
    def authUrl(self):
        return self.__authUrl

    @property
    def authCb(self):
        return self.__authCb
    
    @property
    def clientId(self):
        return self.__clientId

    @clientId.setter
    def clientId(self, value):
        self.__clientId = value

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
    def restHost(self):
        return self.__restHost

    @restHost.setter
    def restHost(self, value):
        self.__restHost = value

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
