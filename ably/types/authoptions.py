from __future__ import absolute_import

import six

from ably.util.exceptions import AblyException


class AuthOptions(object):
    def __init__(self, auth_callback=None, auth_url=None, auth_token=None,
                 auth_headers=None, auth_params=None, key_id=None, key_value=None,
                 key=None, query_time=False):
        self.__auth_callback = auth_callback
        self.__auth_url = auth_url
        self.__auth_token = auth_token
        self.__auth_headers = auth_headers
        self.__auth_params = auth_params
        if key is not None:
            self.__key_id, self.__key_value = self.parse_key(key)
        else:
            self.__key_id = key_id
            self.__key_value = key_value
        self.__query_time = query_time

    def parse_key(self, key):
        try:
            key_id, key_value = key.split(':')
            return key_id, key_value
        except ValueError:
            raise AblyException("key of not len 2 parameters: {0}"
                                .format(key.split(':')),
                                401, 40101)

    def merge(self, other):
        if self.__auth_callback is None:
            self.__auth_callback = other.auth_callback

        if self.__auth_url is None:
            self.__auth_url = other.auth_url

        if self.__key_id is None:
            self.__key_id = other.key_id

        if self.__key_value is None:
            self.__key_value = other.key_value

        if self.__auth_token is None:
            self.__auth_token = other.auth_token

        if self.__auth_headers is None:
            self.__auth_headers = other.auth_headers

        if self.__auth_params is None:
            self.__auth_params = other.auth_params

        self.__query_time == self.__query_time and other.query_time

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
    def key_id(self):
        return self.__key_id

    @key_id.setter
    def key_id(self, value):
        self.__key_id = value

    @property
    def key_value(self):
        return self.__key_value

    @key_value.setter
    def key_value(self, value):
        self.__key_value = value

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
