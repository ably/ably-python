from __future__ import absolute_import

import functools
import itertools
import logging
import time
import json

from six.moves import range
from six.moves.urllib.parse import urljoin

import requests
import msgpack

from ably.rest.auth import Auth
from ably.http.httputils import HttpUtils
from ably.transport.defaults import Defaults
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


def reauth_if_expired(func):
    @functools.wraps(func)
    def wrapper(rest, *args, **kwargs):
        if kwargs.get("skip_auth"):
            return func(rest, *args, **kwargs)

        num_tries = 5
        for i in range(num_tries):
            try:
                return func(rest, *args, **kwargs)
            except AblyException as e:
                if e.code == 40140 and i < (num_tries - 1):
                    rest.reauth()
                    continue
                raise
    return wrapper


class Request(object):
    def __init__(self, method='GET', url='/', headers=None, body=None, skip_auth=False):
        self.__method = method
        self.__headers = headers or {}
        self.__body = body
        self.__skip_auth = skip_auth
        self.__url = url

    def with_relative_url(self, relative_url):
        return Request(self.method, urljoin(self.url, relative_url), self.headers, self.body, self.skip_auth)

    @property
    def method(self):
        return self.__method

    @property
    def url(self):
        return self.__url

    @property
    def headers(self):
        return self.__headers

    @property
    def body(self):
        return self.__body

    @property
    def skip_auth(self):
        return self.__skip_auth


class Response(object):
    """
    Composition for requests.Response with delegation
    """

    def __init__(self, response):
        self.__response = response

    def to_native(self):
        content_type = self.__response.headers.get('content-type')
        if content_type == 'application/x-msgpack':
            return msgpack.unpackb(self.__response.content, encoding='utf-8')
        elif content_type == 'application/json':
            return self.json()
        else:
            raise ValueError("Unsuported content type")

    def __getattr__(self, attr):
        return getattr(self.__response, attr)


class Http(object):
    CONNECTION_RETRY = {
        'single_request_connect_timeout': 4,
        'single_request_read_timeout': 15,
        'max_retry_attempts': 3,
        'cumulative_timeout': 10,
    }

    def __init__(self, ably, options):
        options = options or {}
        self.__ably = ably
        self.__options = options

        self.__session = requests.Session()
        self.__auth = None

    def dump_body(self, body):
        if self.options.use_binary_protocol:
            return msgpack.packb(body, use_bin_type=False)
        else:
            return json.dumps(body, separators=(',', ':'))

    @reauth_if_expired
    def make_request(self, method, path, headers=None, body=None,
                     native_data=None, skip_auth=False, timeout=None):
        fallback_hosts = Defaults.get_fallback_rest_hosts(self.__options)
        if fallback_hosts:
            fallback_hosts.insert(0, self.preferred_host)
            fallback_hosts = itertools.cycle(fallback_hosts)
        if native_data is not None and body is not None:
            raise ValueError("make_request takes either body or native_data")
        elif native_data is not None:
            body = self.dump_body(native_data)
        if body:
            all_headers = HttpUtils.default_post_headers(
                self.options.use_binary_protocol)
        else:
            all_headers = HttpUtils.default_get_headers(
                self.options.use_binary_protocol)

        if not skip_auth:
            if self.auth.auth_mechanism == Auth.Method.BASIC and self.preferred_scheme.lower() == 'http':
                raise AblyException(
                    "Cannot use Basic Auth over non-TLS connections",
                    401,
                    40103)
            all_headers.update(self.auth._get_auth_headers())
        if headers:
            all_headers.update(headers)

        single_request_connect_timeout = self.CONNECTION_RETRY['single_request_connect_timeout']
        single_request_read_timeout = self.CONNECTION_RETRY['single_request_read_timeout']
        if fallback_hosts:
            max_retry_attempts = self.CONNECTION_RETRY['max_retry_attempts']
        else:
            max_retry_attempts = 1
        cumulative_timeout = self.CONNECTION_RETRY['cumulative_timeout']
        requested_at = time.time()
        for retry_count in range(max_retry_attempts):
            host = next(fallback_hosts) if fallback_hosts else self.preferred_host
            if self.options.environment:
                host = self.options.environment + '-' + host

            base_url = "%s://%s:%d" % (self.preferred_scheme,
                                       host,
                                       self.preferred_port)
            url = urljoin(base_url, path)
            request = requests.Request(method, url, data=body, headers=all_headers)
            prepped = self.__session.prepare_request(request)
            try:
                response = self.__session.send(
                    prepped,
                    timeout=(single_request_connect_timeout,
                             single_request_read_timeout))
            except Exception as e:
                # Need to catch `Exception`, see:
                # https://github.com/kennethreitz/requests/issues/1236#issuecomment-133312626

                # if last try or cumulative timeout is done, throw exception up
                time_passed = time.time() - requested_at
                if retry_count == max_retry_attempts - 1 or \
                   time_passed > cumulative_timeout:
                    raise e
            else:
                try:
                    AblyException.raise_for_response(response)
                    return Response(response)
                except AblyException as e:
                    if not e.is_server_error:
                        raise e

    def request(self, request):
        return self.make_request(request.method, request.url, headers=request.headers, body=request.body,
                                 skip_auth=request.skip_auth)

    def get(self, url, headers=None, skip_auth=False, timeout=None):
        return self.make_request('GET', url, headers=headers, skip_auth=skip_auth, timeout=timeout)

    def post(self, url, headers=None, body=None, native_data=None, skip_auth=False, timeout=None):
        return self.make_request('POST', url, headers=headers, body=body, native_data=native_data,
                                 skip_auth=skip_auth, timeout=timeout)

    def delete(self, url, headers=None, skip_auth=False, timeout=None):
        return self.make_request('DELETE', url, headers=headers, skip_auth=skip_auth, timeout=timeout)

    @property
    def auth(self):
        return self.__auth

    @auth.setter
    def auth(self, value):
        self.__auth = value

    @property
    def options(self):
        return self.__options

    @property
    def preferred_host(self):
        return Defaults.get_rest_host(self.options)

    @property
    def preferred_port(self):
        return Defaults.get_port(self.options)

    @property
    def preferred_scheme(self):
        return Defaults.get_scheme(self.options)
