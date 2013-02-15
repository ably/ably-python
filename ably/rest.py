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
    return wrapper


class AblyRest(object):
    def __init__(self, key=None, app_id=None, key_id=None, key_value=None,
            client_id=None, rest_host="rest.ably.io", rest_port=443,
            encrypted=True, auth_token=None, auth_callback=None,
            auth_url=None):
        self.__base_url = 'https://rest.ably.io'

        if key is not None:
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
        self.__encrypted = encrypted

        self.__authority = 'https://%s:%d' % (rest_host, rest_port)
        self.__base_uri = '%s/apps/%s' % (self.__authority, app_id)

        self.__auth = Auth(self, app_id=app_id, key_id=key_id,
                key_value=key_value, auth_token=auth_token,
                auth_callback=auth_callback, auth_url=auth_url, 
                client_id=client_id)

        self.__channels = Channels(self)

    def stats(self, params):
        return self.get('/stats')

    def time(self):
        r = self.get('/time')
        AblyException.raise_for_response(r)
        return r.json()[0]

    def default_get_headers(self):
        return {
            'Accept': 'application/json',
        }

    def default_post_headers(self):
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    @reauth_if_expired
    def get(self, path, headers=None, params=None):
        headers = self.default_get_headers()
        headers.update(headers or {})
        headers.update(self.__auth.get_auth_headers())

        r = requests.get("%s%s" % (self.__base_uri, path), headers=headers)
        AblyException.raise_for_response(r)
        return r

    @reauth_if_expired
    def post(self, path, data=None, headers=None, params=None):
        headers = self.default_post_headers()
        headers.update(headers or {})
        headers.update(self.__auth.get_auth_headers())

        r = requests.post("%s%s" % (self.__base_uri, path), 
                headers=headers, data=data)
        AblyException.raise_for_response(r)
        return r

    @reauth_if_expired
    def delete(self, path, headers=None, params=None):
        headers = dict(headers or {})
        headers.update(self.__auth.get_auth_headers())

        r = requests.delete("%s%s" % (self.__base_uri, path), headers=headers)
        AblyException.raise_for_response(r)
        return r

    @property
    def authority(self):
        return self.__authority

    @property
    def base_uri(self):
        return self.__base_uri

    @property
    def app_id(self):
        return self.__app_id or ""

    @property
    def client_id(self):
        return self.__client_id or ""

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

    @property
    def encrypted(self):
        return self.__encrypted

