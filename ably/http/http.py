from __future__ import absolute_import

import functools
import logging

from six.moves import range
from six.moves.urllib.parse import urljoin

import requests

from ably.http.httputils import HttpUtils
from ably.transport.defaults import Defaults
from ably.types.fallback import Fallback
from ably.util.exceptions import AblyException
from ably.rest.auth import Auth

log = logging.getLogger(__name__)


# Decorator to attempt fallback hosts in case of a host-error

#TODO rm or use 
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


#TODO rm or use
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
    def __init__(self, method='GET', url='/', headers=None, body=None, skip_auth=False, timeout=None):
        self.__method = method
        self.__headers = headers or {}
        self.__body = body
        self.__skip_auth = skip_auth
        self.__url = url
        self.__timeout=timeout

    def with_relative_url(self, relative_url):
        return Request(self.method, urljoin(self.url, relative_url), self.headers, self.body, self.skip_auth)


    @property
    def timeout(self):
        return self.__timeout
    
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

    
class AblyError(object):
    def __init__(self,statusCode=400, code=40000, message=""):
        self.__statusCode = statusCode
        self.__code = code
        self.__message = message

    @property
    def statusCode(self):
        return self.__statusCode

    @property
    def code(self):
        return self.__code

    @property
    def message(self):
        return self.__message

    @staticmethod
    def from_json(json):
        return AblyError(statusCode=json["statusCode"], code=json["code"], message=json["message"])

    def __repr__(self):
        return "message: " + self.message + ", statusCode: " + str(self.statusCode) + ", code: " + str(self.code)

    __str__ = __repr__

    
class Response(object):
    def __init__(self, response):
        self.__response = response
        json = response.json()
        if "error" in json:
            self.__error = AblyError.from_json(json["error"])
        else:
            self.__error = None

        self.__ok = response.status_code >=200 and response.status_code <300


    @property
    def error(self):
        return self.__error
    
    @property
    def ok(self):
        return self.__ok

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

    @property
    def headers(self):
        return self.headers

    @property
    def content_type(self):
        return self.response.headers['Content-Type']

    @property
    def links(self):
        return self.response.links


class Http(object):
    def __init__(self, ably, options):
        options = options or {}
        self.__ably = ably
        self.__options = options
        self.__session = requests.Session()
        self.__auth = None

    #@fallback
    #@reauth_if_expired
    def make_request(self, method, url, headers=None, body=None, skip_auth=False, timeout=None, scheme=None, host=None, port=0):
        scheme = scheme or self.preferred_scheme
        if scheme == "http" and self.__auth.auth_method == Auth.Method.BASIC:
            raise AblyException(reason="Cannot use Basic authentation over http",
                                status_code=400,
                                code=40000)

        host = host or self.preferred_host
        port = port or self.preferred_port
        base_url = "%s://%s:%d" % (scheme, host, port)
        url = urljoin(base_url, url)

        hdrs = headers or {}
        headers = HttpUtils.default_get_headers(not self.options.use_text_protocol)
        headers.update(hdrs)
        

        if not skip_auth:
            headers.update(self.auth._get_auth_headers())


        request = requests.Request(method, url, data=body, headers=headers)
        prepped = self.__session.prepare_request(request)

        # log.debug("Method: %s" % method)
        # log.debug("Url: %s" % url)
        # log.debug("Headers: %s" % headers)
        # log.debug("Body: %s" % body)
        # log.debug("Prepped: %s" % prepped)

        # TODO add timeouts from options here

        result = self.__session.send(prepped)
        response = Response(result)

        if response and response.error is not None:
            if self.handleInvalidToken(response):
                if self.auth.can_request_token():
                    self.auth.authorise(force=True)
                else:
                    raise AblyException(reason="No way to renew invalid token", status_code=401, code=40140)

            elif self.handleFallback(response):
                fb = Fallback(Defaults.get_fallback_hosts(self.options))
                fb_host = ""
                while fb.should_use_fallback(options, response) and fb_host is not None:
                    fb_host = fb.random_host()
                    log.debug("attempting fallback for host " + fb_host)
                    response = self.make_request(method=method,url=url,headers=headers,body=body,skip_auth=skip_auth,timeout=timeout,scheme=scheme,host=fb_host,port=port)

        AblyException.raise_for_response(response)

        return response

    def handleInvalidToken(self, response):
        if response and response.error and response.error.code == 40140:
            return True
        else:
            return False

    def handleFallback(self,response):
        #
        return False
        

    def request(self, request):
        return self.make_request(request.method, request.url, headers=request.headers, body=request.body, timeout=request.timeout)

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

    @options.setter
    def options(setter, value):
        self.__options = value


    @property
    def preferred_host(self):
        return Defaults.get_host(self.options)

    @property
    def preferred_port(self):
        return Defaults.get_port(self.options)

    @property
    def preferred_scheme(self):
        return Defaults.get_scheme(self.options)
