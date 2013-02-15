import functools
import types
import requests

from ably.auth import Auth
from ably.channel import Channels
from ably.exceptions import AblyException


def reauth_if_expired(func):
    @functools.wraps(func)
    def wrapper(rest, *args, **kwargs):
        while True:
            try:
                return func(rest, *args, **kwargs)
            except AblyException as e:
                if e.code == 40140:
                    rest.reauth()
                    continue
                raise


class AblyRest(object):
    def __init__(self, key=None, app_id=None, key_id=None, key_value=None,
            client_id=None, rest_host="rest.ably.io", rest_port=443):
        self.__base_url = 'https://rest.ably.io'

        if not options:
            raise ValueError("no options provided")

        if key is not None
            try:
                app_id, key_id, key_value = key.split(':', 3)
            except ValueError:
                raise ValueError("invalid key parameter: %s" % key)

        if not app_id:
            raise ValueError("no app_id provided")

        self.__app_id = app_id
        self.__key_id = key_id
        self.__key_value = key_value
        self.__client_id = client_id
        self.__rest_host = rest_host
        self.__rest_port = rest_port

        self.__authority = 'https://%s:%d' % (rest_host, rest_port)
        self.__base_uri = '%s/apps/%s' % (self.__authority, app_id)

        self.__auth = Auth(self, options)
        self.__channels = Channels(self)

    def stats(self, params):
        return self.get('/stats')

    def time(self):
        r = requests.get(self.__base_url + '/time')
        AblyException.raise_for_response(r)
        return r.json[0]

    @reauth_if_expired
    def get(self, path, headers=None, params=None):
        headers = dict(headers or {})
        headers.update(self.__auth.get_auth_headers())

        r = requests.get(self.__base_uri + path, headers=headers)
        AblyException.raise_for_response(r)
        return r

    @reauth_if_expired
    def post(self, path, body=None, headers=None, params=None):
        headers = dict(headers or {})
        headers.update(self.__auth.get_auth_headers())

        r = requests.post(self.__base_uri + path, headers=headers, data=body)
        AblyException.raise_for_response(r)
        return r

    @reauth_if_expired
    def delete(self, path, headers=None, params=None):
        header = dict(headers or {})
        headers.update(self.__auth.get_auth_headers())

        r.requests.delete(self.__base_uri + path, headers=headers, data=body)
        AblyException.raise_for_response(r)
        return r

    @property
    def app_id(self):
        return self.__app_id || ""

    @property
    def client_id(self):
        return self.__client_id || ""

    @property
    def rest_host(self):
        return self.__rest_host

    @property
    def rest_port(self):
        return self.__rest_port

    @property
    def channels(self):
        return self.__channels

    @property
    def auth(self):
        return self.__auth

