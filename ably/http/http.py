from __future__ import absolute_import

import functools
import urlparse

import requests

from ably.http.httputils import HttpUtils
from ably.transport.defaults import Defaults
from ably.util.exceptions import AblyException

# Decorator to attempt fallback hosts in case of a host-error
def fallback(func):
    @functools.wraps(func)
    def wrapper(http, *args, **kwargs):
        try:
            return func(http, *args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            # if we cannot attempt a fallback, re-raise
            # TODO: See if we can determine why this failed
            fallback_hosts = Defaults.get_fallback_hosts(http.options)
            if kwargs.get("host") or not fallback_hosts:
                raise

        last_exception = None
        for host in fallback_hosts:
            try:
                kwargs["host"] = host
                return func(rest, *args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                # TODO: as above
                last_exception = e

        raise last_exception
    return wrapper

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


class Request(object):
    def __init__(self, method='GET', url='/', headers=None, body=None, skip_auth=False):
        self.__method = method
        self.__headers = headers or {}
        self.__body = body
        self.__skip_auth = skip_auth
        self.__url = url

    def with_relative_url(self, relative_url):
        return Request(self.method, urlparse.urljoin(self.url, relative_url), self.headers, self.body, self.skip_auth)

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
    def __init__(self, response):
        self.__response = response

    def json(self):
        return self.response.json()

    @property
    def response(self):
        return self.__response

    @property
    def text(self):
        return self.response.text

    @property
    def status_code(self):
        return self.response.status_code


class Http(object):
    def __init__(self, ably, options):
        options = options or {}
        self.__ably = ably
        self.__options = options

        self.__session = requests.Session()
        self.__auth = None

    @fallback
    @reauth_if_expired
    def make_request(self, method, url, headers=None, body=None, skip_auth=False, timeout=None):
        url = urlparse.urljoin(self.preferred_host, url)

        hdrs = headers or {}
        headers = HttpUtils.default_get_headers(not self.options.use_text_protocol)
        headers.update(hdrs)

        if not skip_auth:
            headers.update(self.http.auth._get_auth_headers())

        response = requests.Request(method, url, data=body, headers=headers)
        AblyException.raise_for_response(response)

        return Response(response)

    def request(self, request):
        return self.make_request(request.method, request.url, headers=request.headers, body=request.body)

    def get(self, url, headers=None, skip_auth=False, timeout=None):
        return self.make_request('GET', url, headers=headers, skip_auth=skip_auth, timeout=timeout)

    def post(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return self.make_request('POST', url, headers=headers, body=body, skip_auth=skip_auth, timeout=timeout)

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
        return Defaults.get_host(self.options)
