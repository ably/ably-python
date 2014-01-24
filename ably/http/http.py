from __future__ import absolute_import

import urlparse

import requests


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


class Http(object):
    def __init__(self, ably, options=None):
        options = options or {}
        self._ably = ably
        self._options = options

        self._scheme = 'https' if options.tls else 'http'
        self._port = Defaults.get_port(options)
        
        self._session = requests.Session()

    def make_request(self, method, url, headers=None, body=None):

    def make_request(self, request):
        url = urlparse.urljoin(self.base_url, request.url)
        response = requests.Request(request.method, url, data=request.body, headers=request.headers)
        return Response(response)
