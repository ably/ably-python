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
    def __init__(self, ably, **options):
        options = options or {}
        self._ably = ably
        self._options = options

        self._scheme = 'https' if options.get('tls') else 'http'
        self._port = Defaults.get_port(options)
        
        self._session = requests.Session()

    @fallback
    @reauth_if_expired
    def make_request(self, method, url, headers=None, body=None, skip_auth=False, timeout=None):
        url = urlparse.urljoin(self.base_url, url)

        hdrs = headers or {}
        headers = self._default_get_headers()
        headers.update(hdrs)

        if not skip_auth:
            headers.update(self.http.auth._get_auth_headers())

        prefix = self._get_prefix(scheme=scheme, host=host, port=port)

        response = requests.Request(method, url, data=body, headers=headers)
        AblyException.raise_for_response(response)

        return Response(response)

    def make_request(self, request):
        return self.make_request(request.method, request.url, headers=request.headers, body=request.body)

    def get(self, url, headers=None, skip_auth=False, timeout=None):
        return self.make_request('GET', url, headers=headers, skip_auth=skip_auth, timeout=timeout)

    def post(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return self.make_request('POST', url, headers=headers, body=body, skip_auth=skip_auth, timeout=timeout)

    def delete(self, url, headers=None, skip_auth=False timeout=None):
        return self.make_request('DELETE', url, headers=headers, skip_auth=skip_auth, timeout=timeout)
