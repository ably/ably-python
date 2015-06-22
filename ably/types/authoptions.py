from __future__ import absolute_import

import six

from ably.util.exceptions import AblyException


class AuthOptions(object):
    def __init__(self, auth_callback=None, auth_url=None, auth_token=None,
                 auth_headers=None, auth_params=None, keyId=None, keyValue=None,
                 query_time=False, capability="", useTokenAuth=False):
        self.__auth_callback = auth_callback
        self.__auth_url = auth_url
        self.__auth_token = auth_token
        self.__auth_headers = auth_headers
        self.__auth_params = auth_params
        self.__keyId = keyId
        self.__keyValue = keyValue
        self.__query_time = query_time
        self.__capability = capability
        self.__useTokenAuth= useTokenAuth

    @classmethod
    def with_key(cls, key, **kwargs):
        kwargs = kwargs or {}

        key_components = key.split(':')

        if len(key_components) != 2:
            raise AblyException("invalid key parameter", 401, 40101)

        kwargs['keyId'] = key_components[0]
        kwargs['keyValue'] = key_components[1]

        return cls(**kwargs)

    def merge(self, other):
        if self.__auth_callback is None:
            self.__auth_callback = other.auth_callback

        if self.__auth_url is None:
            self.__auth_url = other.auth_url

        if self.__keyId is None:
            self.__keyId = other.keyId

        if self.__keyValue is None:
            self.__keyValue = other.keyValue

        if self.__auth_token is None:
            self.__auth_token = other.auth_token

        if self.__auth_headers is None:
            self.__auth_headers = other.auth_headers

        if self.__auth_params is None:
            self.__auth_params = other.auth_params

        self.__query_time == self.__query_time and other.query_time


    @property
    def  useTokenAuth(self):
        return self.__useTokenAuth
    
    @property
    def capability(self):
        return self.__capability
    
    @property
    def auth_callback(self):
        return self.__auth_callback

    @auth_callback.setter
    def auth_callback(self, value):
        self.__auth_callback = value

    @property
    def auth_url(self):
        return self.__auth_url

    @auth_url.setter
    def auth_url(self, value):
        self.__auth_url = value

    @property
    def keyId(self):
        return self.__keyId

    @keyId.setter
    def keyId(self, value):
        self.__keyId = value

    @property
    def keyValue(self):
        return self.__keyValue

    @keyValue.setter
    def keyValue(self, value):
        self.__keyValue = value

    @property
    def auth_token(self):
        return self.__auth_token

    @auth_token.setter
    def auth_token(self, value):
        self.__auth_token = value

    @property
    def auth_headers(self):
        return self.__auth_headers

    @auth_headers.setter
    def auth_headers(self, value):
        self.__auth_headers = value

    @property
    def auth_params(self):
        return self.__auth_params

    @auth_params.setter
    def auth_params(self, value):
        self.__auth_params = value

    @property
    def query_time(self):
        return self.__query_time

    @query_time.setter
    def query_time(self, value):
        self.__query_time = value

    def __unicode__(self):
        return six.text_type(self.__dict__)
