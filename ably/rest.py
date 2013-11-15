import functools
import logging
import types

import requests

from ably.auth import Auth
from ably.channel import Channels
from ably.exceptions import AblyException, catch_all

log = logging.getLogger(__name__)

# Decorator to attempt fallback hosts in case of a host-error
def fallback(func):
    @functools.wraps(func)
    def wrapper(rest, *args, **kwargs):
        try:
            return func(rest, *args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            # if we cannot attempt a fallback, re-raise
            # TODO: See if we can determine why this failed
            if kwargs.get("host") or not rest._fallback_hosts:
                raise

        last_exception = None
        for host in rest._fallback_hosts:
            try:
                kwargs["host"] = host
                return func(rest, *args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                # TODO: as above
                last_exception = e

        raise last_exception

def reauth_if_expired(func):
    @functools.wraps(func)
    def wrapper(rest, *args, **kwargs):
        if kwargs.get("skip_auth"):
            return func(rest, *args, **kwargs)

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
    """Ably Rest Client"""
    def __init__(self, key=None, key_id=None, key_value=None,
                 client_id=None, host="rest.ably.io", port=80, tls_port=443,
                 tls=True, auth_token=None, auth_callback=None,
                 auth_url=None, keep_alive=True, fallback_hosts=None):
        """Create an AblyRest instance.

        :Parameters:
          **Credentials**
          - `key`: a valid key string

          **Or**
          - `key_id`: Your Ably key id
          - `key_value`: Your Ably key value

          **Optional Parameters**
          - `client_id`: Undocumented
          - `host`: The host to connect to. Defaults to rest.ably.io
          - `port`: The port to connect to. Defaults to 80
          - `tls_port`: The tls_port to connect to. Defaults to 443
          - `tls`: Specifies whether the client should use TLS. Defaults
            to True
          - `auth_token`: Undocumented
          - `auth_callback`: Undocumented
          - `auth_url`: Undocumented
          - `keep_alive`: use persistent connections. Defaults to True
        """

        if key is not None:
            try:
                key_id, key_value = key.split(':', 2)
            except ValueError:
                msg = "invalid key parameter: %s" % key
                raise AblyException(msg, 401, 40101)

        self.__key_id = key_id
        self.__key_value = key_value
        self.__client_id = client_id
        self.__host = host
        self.__port = port
        self.__tls_port = tls_port
        self.__tls = tls
        self.__keep_alive = bool(keep_alive)
        self.__fallback_hosts = fallback_hosts

        if self.__keep_alive:
            self.__session = requests.Session()
        else:
            self.__session = None

        self.__scheme = 'https' if tls else 'http'
        self.__port = tls_port if tls else port
        self.__authority = '%s://%s:%d' % (self.__scheme, host, self.__port)

        self.__auth = Auth(self, key_id=key_id,
                           key_value=key_value, auth_token=auth_token,
                           auth_callback=auth_callback, auth_url=auth_url,
                           client_id=client_id)

        self.__channels = Channels(self)

    @catch_all
    def stats(self, direction=None, start=None, end=None, params=None,
              timeout=None):
        """Returns the stats for this application"""
        params = params or {}

        if direction:
            params["direction"] = direction
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        return self._get('/stats', params=params, timeout=timeout).json()

    @catch_all
    def time(self, timeout=None):
        """Returns the current server time in ms since the unix epoch"""
        r = self._get('/time', skip_auth=True,
                      timeout=timeout)
        AblyException.raise_for_response(r)
        return r.json()[0]

    def _default_get_headers(self):
        return {
            'Accept': 'application/json',
        }

    def _default_post_headers(self):
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def _get_prefix(self, scheme=None, host=None, port=None):
        scheme = scheme or self.__scheme
        host = host or self.__host
        port = port or self.__port

        return '%s://%s:%d' % (scheme, host, port)

    @fallback
    @reauth_if_expired
    def _get(self, path, headers=None, params=None, skip_auth=False,
            timeout=None, scheme=None, host=None, port=None):
        hdrs = headers or {}
        headers = self._default_get_headers()
        headers.update(hdrs)

        if not skip_auth:
            headers.update(self.__auth._get_auth_headers())

        prefix = self._get_prefix(scheme=scheme, host=host, port=port)

        r = self._requests.get("%s%s" % (prefix, path), headers=headers,
                               timeout=timeout)
        AblyException.raise_for_response(r)
        return r

    @fallback
    @reauth_if_expired
    def _post(self, path, data=None, headers=None, params=None,
              timeout=None, scheme=None, host=None, port=None):
        hdrs = headers or {}
        headers = self._default_post_headers()
        headers.update(hdrs)
        headers.update(self.__auth._get_auth_headers())

        prefix = self._get_prefix(scheme=scheme, host=host, port=port)

        r = self._requests.post("%s%s" % (prefix, path), headers=headers,
                                data=data, timeout=timeout)
        AblyException.raise_for_response(r)
        return r

    @fallback
    @reauth_if_expired
    def _delete(self, path, headers=None, params=None, timeout=None,
            scheme=None, host=None, port=None):
        headers = dict(headers or {})
        headers.update(self.__auth._get_auth_headers())

        prefix = self._get_prefix(scheme=scheme, host=host, port=port)

        r = self._requests.delete("%s%s" % (prefix, path), headers=headers,
                                  timeout=timeout)
        AblyException.raise_for_response(r)
        return r

    @property
    def client_id(self):
        return self.__client_id or ""

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def tls_port(self):
        return self.__tls_port

    @property
    def channels(self):
        """Returns the channels container object"""
        return self.__channels

    @property
    def auth(self):
        return self.__auth

    @property
    def tls(self):
        return self.__tls

    @property
    def scheme(self):
        return self.__scheme

    @property
    def keep_alive(self):
        return self.__keep_alive

    @property
    def _requests(self):
        return self.__session if self.__keep_alive else requests

    @property
    def _fallback_hosts(self):
        return self.__fallback_hosts
