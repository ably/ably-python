import functools
import logging
import time
import json
from urllib.parse import urljoin

import requests
import msgpack

from ably.rest.auth import Auth
from ably.http.httputils import HttpUtils
from ably.transport.defaults import Defaults
from ably.util.exceptions import AblyException, AblyAuthException

log = logging.getLogger(__name__)


def reauth_if_expired(func):
    @functools.wraps(func)
    def wrapper(rest, *args, **kwargs):
        if kwargs.get("skip_auth"):
            return func(rest, *args, **kwargs)

        # RSA4b1 Detect expired token to avoid round-trip request
        auth = rest.auth
        token_details = auth.token_details
        if token_details and auth.time_offset is not None and auth.token_details_has_expired():
            rest.reauth()
            retried = True
        else:
            retried = False

        try:
            return func(rest, *args, **kwargs)
        except AblyException as e:
            if 40140 <= e.code < 40150 and not retried:
                rest.reauth()
                return func(rest, *args, **kwargs)

            raise

    return wrapper


class Request:
    def __init__(self, method='GET', url='/', headers=None, body=None,
                 skip_auth=False, raise_on_error=True):
        self.__method = method
        self.__headers = headers or {}
        self.__body = body
        self.__skip_auth = skip_auth
        self.__url = url
        self.raise_on_error = raise_on_error

    def with_relative_url(self, relative_url):
        url = urljoin(self.url, relative_url)
        return Request(self.method, url, self.headers, self.body,
                       self.skip_auth, self.raise_on_error)

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


class Response:
    """
    Composition for requests.Response with delegation
    """

    def __init__(self, response):
        self.__response = response

    def to_native(self):
        content = self.__response.content
        if not content:
            return None

        content_type = self.__response.headers.get('content-type')
        if content_type == 'application/x-msgpack':
            return msgpack.unpackb(content)
        elif content_type == 'application/json':
            return self.__response.json()
        else:
            raise ValueError("Unsuported content type")

    @property
    def response(self):
        return self.__response

    def __getattr__(self, attr):
        return getattr(self.__response, attr)


class Http:
    CONNECTION_RETRY_DEFAULTS = {
        'http_open_timeout': 4,
        'http_request_timeout': 10,
        'http_max_retry_duration': 15,
    }

    __session = requests.Session()

    def __init__(self, ably, options):
        options = options or {}
        self.__ably = ably
        self.__options = options
        self.__auth = None
        # Cached fallback host (RSC15f)
        self.__host = None
        self.__host_expires = None

    def dump_body(self, body):
        if self.options.use_binary_protocol:
            return msgpack.packb(body, use_bin_type=False)
        else:
            return json.dumps(body, separators=(',', ':'))

    def reauth(self):
        try:
            self.auth.authorize()
        except AblyAuthException as e:
            if e.code == 40101:
                e.message = ("The provided token is not renewable and there is"
                             " no means to generate a new token")
            raise e

    def get_rest_hosts(self):
        hosts = self.options.get_rest_hosts()
        host = self.__host
        if host is None:
            return hosts

        if time.time() > self.__host_expires:
            self.__host = None
            self.__host_expires = None
            return hosts

        hosts = list(hosts)
        hosts.remove(host)
        hosts.insert(0, host)
        return hosts

    @reauth_if_expired
    def make_request(self, method, path, headers=None, body=None,
                     skip_auth=False, timeout=None, raise_on_error=True):

        if body is not None and type(body) not in (bytes, str):
            body = self.dump_body(body)

        if body:
            all_headers = HttpUtils.default_post_headers(
                self.options.use_binary_protocol, self.__ably.variant)
        else:
            all_headers = HttpUtils.default_get_headers(
                self.options.use_binary_protocol, self.__ably.variant)

        if not skip_auth:
            if self.auth.auth_mechanism == Auth.Method.BASIC and self.preferred_scheme.lower() == 'http':
                raise AblyException(
                    "Cannot use Basic Auth over non-TLS connections",
                    401,
                    40103)
            all_headers.update(self.auth._get_auth_headers())
        if headers:
            all_headers.update(headers)

        timeout = (self.http_open_timeout, self.http_request_timeout)
        http_max_retry_duration = self.http_max_retry_duration
        requested_at = time.time()

        hosts = self.get_rest_hosts()
        for retry_count, host in enumerate(hosts):
            base_url = "%s://%s:%d" % (self.preferred_scheme,
                                       host,
                                       self.preferred_port)
            url = urljoin(base_url, path)
            request = requests.Request(method, url, data=body, headers=all_headers)
            prepped = self.__session.prepare_request(request)
            try:
                response = self.__session.send(prepped, timeout=timeout)
            except Exception as e:
                # Need to catch `Exception`, see:
                # https://github.com/kennethreitz/requests/issues/1236#issuecomment-133312626

                # if last try or cumulative timeout is done, throw exception up
                time_passed = time.time() - requested_at
                if retry_count == len(hosts) - 1 or time_passed > http_max_retry_duration:
                    raise e
            else:
                try:
                    if raise_on_error:
                        AblyException.raise_for_response(response)

                    # Keep fallback host for later (RSC15f)
                    if retry_count > 0 and host != self.options.get_rest_host():
                        self.__host = host
                        self.__host_expires = time.time() + (self.options.fallback_retry_timeout / 1000.0)

                    return Response(response)
                except AblyException as e:
                    if not e.is_server_error:
                        raise e

                    # if last try or cumulative timeout is done, throw exception up
                    time_passed = time.time() - requested_at
                    if retry_count == len(hosts) - 1 or time_passed > http_max_retry_duration:
                        raise e

    def delete(self, url, headers=None, skip_auth=False, timeout=None):
        return self.make_request('DELETE', url, headers=headers,
                                 skip_auth=skip_auth, timeout=timeout)

    def get(self, url, headers=None, skip_auth=False, timeout=None):
        return self.make_request('GET', url, headers=headers,
                                 skip_auth=skip_auth, timeout=timeout)

    def patch(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return self.make_request('PATCH', url, headers=headers, body=body,
                                 skip_auth=skip_auth, timeout=timeout)

    def post(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return self.make_request('POST', url, headers=headers, body=body,
                                 skip_auth=skip_auth, timeout=timeout)

    def put(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return self.make_request('PUT', url, headers=headers, body=body,
                                 skip_auth=skip_auth, timeout=timeout)

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
        return self.options.get_rest_host()

    @property
    def preferred_port(self):
        return Defaults.get_port(self.options)

    @property
    def preferred_scheme(self):
        return Defaults.get_scheme(self.options)

    @property
    def http_open_timeout(self):
        if self.options.http_open_timeout is not None:
            return self.options.http_open_timeout
        return self.CONNECTION_RETRY_DEFAULTS['http_open_timeout']

    @property
    def http_request_timeout(self):
        if self.options.http_request_timeout is not None:
            return self.options.http_request_timeout
        return self.CONNECTION_RETRY_DEFAULTS['http_request_timeout']

    @property
    def http_max_retry_count(self):
        if self.options.http_max_retry_count is not None:
            return self.options.http_max_retry_count
        return self.CONNECTION_RETRY_DEFAULTS['http_max_retry_count']

    @property
    def http_max_retry_duration(self):
        if self.options.http_max_retry_duration is not None:
            return self.options.http_max_retry_duration
        return self.CONNECTION_RETRY_DEFAULTS['http_max_retry_duration']
