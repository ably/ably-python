from __future__ import absolute_import

import base64
import logging
import random
import time

import six
import requests

from ably.types.capability import Capability
from ably.types.tokendetails import TokenDetails
from ably.types.tokenrequest import TokenRequest
from ably.util.exceptions import AblyException

# initialise and seed our own instance of random
rnd = random.Random()
rnd.seed()

__all__ = ["Auth"]

log = logging.getLogger(__name__)


class Auth(object):

    class Method:
        BASIC = "BASIC"
        TOKEN = "TOKEN"

    def __init__(self, ably, options):
        self.__ably = ably
        self.__auth_options = options

        self.__basic_credentials = None
        self.__auth_params = None
        self.__token_details = None

        must_use_token_auth = options.use_token_auth is True
        must_not_use_token_auth = options.use_token_auth is False
        can_use_basic_auth = options.key_secret is not None and options.client_id is None
        if not must_use_token_auth and can_use_basic_auth:
            # We have the key, no need to authenticate the client
            # default to using basic auth
            log.debug("anonymous, using basic auth")
            self.__auth_mechanism = Auth.Method.BASIC
            basic_key = "%s:%s" % (options.key_name, options.key_secret)
            basic_key = base64.b64encode(basic_key.encode('utf-8'))
            self.__basic_credentials = basic_key.decode('ascii')
            return
        elif must_not_use_token_auth and not can_use_basic_auth:
            raise ValueError('If use_token_auth is False you must provide a key')

        # Using token auth
        self.__auth_mechanism = Auth.Method.TOKEN

        if options.token_details:
            self.__token_details = options.token_details
        elif options.auth_token:
            self.__token_details = TokenDetails(token=options.auth_token)
        else:
            self.__token_details = None

        if options.auth_callback:
            log.debug("using token auth with auth_callback")
        elif options.auth_url:
            log.debug("using token auth with auth_url")
        elif options.key_secret:
            log.debug("using token auth with client-side signing")
        elif options.auth_token:
            log.debug("using token auth with supplied token only")
        elif options.token_details:
            log.debug("using token auth with supplied token_details")
        else:
            raise ValueError("Can't authenticate via token, must provide "
                             "auth_callback, auth_url, key, token or a TokenDetail")

    def authorise(self, force=False, **kwargs):
        self.__auth_mechanism = Auth.Method.TOKEN

        if self.__token_details:
            if self.__token_details.expires > self._timestamp():
                if not force:
                    log.debug(
                        "using cached token; expires = %d",
                        self.__token_details.expires
                    )
                    return self.__token_details
            else:
                # token has expired
                self.__token_details = None

        self.__token_details = self.request_token(**kwargs)
        return self.__token_details

    def request_token(self, key_name=None, key_secret=None, query_time=None,
                      auth_token=None, auth_callback=None, auth_url=None,
                      auth_headers=None, auth_method=None, auth_params=None,
                      token_params=None, ttl=None, capability=None,
                      client_id=None, timestamp=None):
        key_name = key_name or self.auth_options.key_name
        key_secret = key_secret or self.auth_options.key_secret

        log.debug("Auth callback: %s" % auth_callback)
        log.debug("Auth options: %s" % six.text_type(self.auth_options))
        if query_time is None:
            query_time = self.auth_options.query_time
        query_time = bool(query_time)
        auth_token = auth_token or self.auth_options.auth_token
        auth_callback = auth_callback or self.auth_options.auth_callback
        auth_url = auth_url or self.auth_options.auth_url

        auth_params = auth_params or self.auth_options.auth_params or {}

        auth_method = (auth_method or self.auth_options.auth_method).upper()

        token_params = token_params or {}

        token_params.setdefault("client_id", self.ably.client_id)

        log.debug("Token Params: %s" % token_params)
        if auth_callback:
            log.debug("using token auth with authCallback")
            token_request = auth_callback(**token_params)
        elif auth_url:
            log.debug("using token auth with authUrl")

            # circular dependency
            from ably.http.http import Response
            response = Response(requests.request(auth_method, auth_url,
                                                 headers=auth_headers,
                                                 params=auth_params))

            AblyException.raise_for_response(response)
            try:
                token_request = response.to_native()
            except ValueError:
                token_request = response.text
        else:
            token_request = self.create_token_request(
                key_name=key_name,
                key_secret=key_secret,
                query_time=query_time,
                token_params=token_params
                )

        if isinstance(token_request, TokenDetails):
            return token_request
        elif isinstance(token_request, dict) and 'issued' in token_request:
            return TokenDetails.from_dict(token_request)
        elif isinstance(token_request, dict):
            token_request = TokenRequest(**token_request)
        elif isinstance(token_request, six.text_type):
            return TokenDetails(token=token_request)

        # elif key_secret:
        #     log.debug("using token auth with client-side signing")
        #     signed_token_request = self.create_token_request(
        #         key_name=key_name,
        #         key_secret=key_secret,
        #         query_time=query_time,
        #         token_params=token_params)
        # else:
        #     log.debug('No auth_callback, auth_url or key_secret specified')
        #     raise AblyException(
        #         "Auth.request_token() must include valid auth parameters",
        #         400,
        #         40000)

        token_path = "/keys/%s/requestToken" % key_name

        response = self.ably.http.post(
            token_path,
            headers=auth_headers,
            native_data=token_request.to_dict(),
            skip_auth=True
        )

        AblyException.raise_for_response(response)
        response_dict = response.to_native()
        log.debug("Token: %s" % str(response_dict.get("token")))
        return TokenDetails.from_dict(response_dict)

    def create_token_request(self, key_name, key_secret,
                             query_time=None, token_params=None):
        token_params = token_params or {}
        token_request = {}

        if token_params.setdefault("id", key_name) != key_name:
            raise AblyException("Incompatible key specified", 401, 40102)
        token_request['key_name'] = key_name

        if not key_name or not key_secret:
            log.debug('key_name or key_secret blank')
            raise AblyException("No key specified", 401, 40101)

        if query_time is None:
            query_time = self.auth_options.query_time

        if not token_params.get("timestamp"):
            if query_time:
                timestamp = self.ably.time()
            else:
                timestamp = self._timestamp()
        else:
            timestamp = token_params["timestamp"]

        token_request["timestamp"] = int(timestamp)

        token_request['ttl'] = token_params.get('ttl',
                                                TokenDetails.DEFAULTS['ttl'])

        if token_params.get("capability") is None:
            token_request["capability"] = ""
        else:
            token_request['capability'] = six.text_type(
                Capability(token_params["capability"])
            )

        if token_params.get("client_id") is None:
            token_request["client_id"] = ""

        if not token_params.get("nonce"):
            # Note: There is no expectation that the client
            # specifies the nonce; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes
            token_request["nonce"] = self._random()
        else:
            token_request["nonce"] = token_params["nonce"]

        token_request = TokenRequest(**token_request)

        if not token_params.get('mac'):
            token_request.sign_request(key_secret.encode('utf8'))
        else:
            token_request.mac = token_params["mac"]

        return token_request

    @property
    def ably(self):
        return self.__ably

    @property
    def auth_mechanism(self):
        return self.__auth_mechanism

    @property
    def auth_options(self):
        return self.__auth_options

    @property
    def auth_params(self):
        return self.__auth_params

    @property
    def basic_credentials(self):
        return self.__basic_credentials

    @property
    def token_credentials(self):
        if self.__token_details:
            token = self.__token_details.token
            token_key = base64.b64encode(token.encode('utf-8'))
            return token_key.decode('ascii')

    @property
    def token_details(self):
        return self.__token_details

    def _get_auth_headers(self):
        if self.__auth_mechanism == Auth.Method.BASIC:
            return {
                'Authorization': 'Basic %s' % self.basic_credentials,
            }
        else:
            self.authorise()
            return {
                'Authorization': 'Bearer %s' % self.token_credentials,
            }

    def _timestamp(self):
        """Returns the local time in milliseconds since the unix epoch"""
        return int(time.time() * 1000)

    def _random(self):
        return "%016d" % rnd.randint(0, 9999999999999999)
