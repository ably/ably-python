import base64
from datetime import timedelta
import logging
import time
import uuid
import warnings

import requests

from ably.types.capability import Capability
from ably.types.tokendetails import TokenDetails
from ably.types.tokenrequest import TokenRequest
from ably.util.exceptions import AblyException, IncompatibleClientIdException

__all__ = ["Auth"]

log = logging.getLogger(__name__)


class Auth:

    class Method:
        BASIC = "BASIC"
        TOKEN = "TOKEN"

    def __init__(self, ably, options):
        self.__ably = ably
        self.__auth_options = options
        if options.token_details:
            self.__client_id = options.token_details.client_id
        else:
            self.__client_id = options.client_id
        self.__client_id_validated = False

        self.__basic_credentials = None
        self.__auth_params = None
        self.__token_details = None
        self.__time_offset = None

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

    def __authorize_when_necessary(self, token_params=None, auth_options=None, force=False):
        self.__auth_mechanism = Auth.Method.TOKEN

        if token_params is None:
            token_params = dict(self.auth_options.default_token_params)
        else:
            self.auth_options.default_token_params = dict(token_params)
            self.auth_options.default_token_params.pop('timestamp', None)

        if auth_options is not None:
            self.auth_options.replace(auth_options)
        auth_options = dict(self.auth_options.auth_options)
        if self.client_id is not None:
            token_params['client_id'] = self.client_id

        token_details = self.__token_details
        if not force and not self.token_details_has_expired():
            log.debug("using cached token; expires = %d",
                      token_details.expires)
            return token_details

        self.__token_details = self.request_token(token_params, **auth_options)
        self._configure_client_id(self.__token_details.client_id)
        return self.__token_details

    def token_details_has_expired(self):
        token_details = self.__token_details
        if token_details is None:
            return True

        expires = token_details.expires
        if expires is None:
            return False

        timestamp = self._timestamp()
        if self.__time_offset:
            timestamp += self.__time_offset

        return expires < timestamp + token_details.TOKEN_EXPIRY_BUFFER

    def authorize(self, token_params=None, auth_options=None):
        return self.__authorize_when_necessary(token_params, auth_options, force=True)

    def authorise(self, *args, **kwargs):
        warnings.warn(
            "authorise is deprecated and will be removed in v2.0, please use authorize",
            DeprecationWarning)
        return self.authorize(*args, **kwargs)

    def request_token(self, token_params=None,
                      # auth_options
                      key_name=None, key_secret=None, auth_callback=None,
                      auth_url=None, auth_method=None, auth_headers=None,
                      auth_params=None, query_time=None):
        token_params = token_params or {}
        token_params = dict(self.auth_options.default_token_params,
                            **token_params)
        key_name = key_name or self.auth_options.key_name
        key_secret = key_secret or self.auth_options.key_secret

        log.debug("Auth callback: %s" % auth_callback)
        log.debug("Auth options: %s" % self.auth_options)
        if query_time is None:
            query_time = self.auth_options.query_time
        query_time = bool(query_time)
        auth_callback = auth_callback or self.auth_options.auth_callback
        auth_url = auth_url or self.auth_options.auth_url

        auth_params = auth_params or self.auth_options.auth_params or {}

        auth_method = (auth_method or self.auth_options.auth_method).upper()

        auth_headers = auth_headers or self.auth_options.auth_headers or {}

        log.debug("Token Params: %s" % token_params)
        if auth_callback:
            log.debug("using token auth with authCallback")
            token_request = auth_callback(token_params)
        elif auth_url:
            log.debug("using token auth with authUrl")

            token_request = self.token_request_from_auth_url(
                auth_method, auth_url, token_params, auth_headers, auth_params)
        else:
            token_request = self.create_token_request(
                token_params, key_name=key_name, key_secret=key_secret,
                query_time=query_time)
        if isinstance(token_request, TokenDetails):
            return token_request
        elif isinstance(token_request, dict) and 'issued' in token_request:
            return TokenDetails.from_dict(token_request)
        elif isinstance(token_request, dict):
            token_request = TokenRequest.from_json(token_request)
        elif isinstance(token_request, str):
            return TokenDetails(token=token_request)

        token_path = "/keys/%s/requestToken" % token_request.key_name

        response = self.ably.http.post(
            token_path,
            headers=auth_headers,
            body=token_request.to_dict(),
            skip_auth=True
        )

        AblyException.raise_for_response(response)
        response_dict = response.to_native()
        log.debug("Token: %s" % str(response_dict.get("token")))
        return TokenDetails.from_dict(response_dict)

    def create_token_request(self, token_params=None,
                             key_name=None, key_secret=None, query_time=None):
        token_params = token_params or {}
        token_request = {}

        key_name = key_name or self.auth_options.key_name
        key_secret = key_secret or self.auth_options.key_secret
        if not key_name or not key_secret:
            log.debug('key_name or key_secret blank')
            raise AblyException("No key specified: no means to generate a token", 401, 40101)

        token_request['key_name'] = key_name
        if token_params.get('timestamp'):
            token_request['timestamp'] = token_params['timestamp']
        else:
            if query_time is None:
                query_time = self.auth_options.query_time

            if query_time:
                if self.__time_offset is None:
                    server_time = self.ably.time()
                    local_time = self._timestamp()
                    self.__time_offset = server_time - local_time
                    token_request['timestamp'] = server_time
                else:
                    local_time = self._timestamp()
                    token_request['timestamp'] = local_time + self.__time_offset
            else:
                token_request['timestamp'] = self._timestamp()

        token_request['timestamp'] = int(token_request['timestamp'])

        ttl = token_params.get('ttl')
        if ttl is not None:
            if isinstance(ttl, timedelta):
                ttl = ttl.total_seconds() * 1000
            token_request['ttl'] = int(ttl)

        capability = token_params.get('capability')
        if capability is not None:
            token_request['capability'] = str(Capability(capability))

        token_request["client_id"] = (
            token_params.get('client_id') or self.client_id)

        # Note: There is no expectation that the client
        # specifies the nonce; this is done by the library
        # However, this can be overridden by the client
        # simply for testing purposes
        token_request["nonce"] = token_params.get('nonce') or self._random_nonce()

        token_request = TokenRequest(**token_request)

        if token_params.get('mac') is None:
            # Note: There is no expectation that the client
            # specifies the mac; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes.
            token_request.sign_request(key_secret.encode('utf8'))
        else:
            token_request.mac = token_params['mac']

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

    @property
    def client_id(self):
        return self.__client_id

    @property
    def time_offset(self):
        return self.__time_offset

    def _configure_client_id(self, new_client_id):
        # If new client ID from Ably is a wildcard, but preconfigured clientId is set,
        # then keep the existing clientId
        if self.client_id != '*' and new_client_id == '*':
            self.__client_id_validated = True
            return

        # If client_id is defined and not a wildcard, prevent it changing, this is not supported
        if self.client_id is not None and self.client_id != '*' and new_client_id != self.client_id:
            raise IncompatibleClientIdException(
                "Client ID is immutable once configured for a client. "
                "Client ID cannot be changed to '{}'".format(new_client_id), 400, 40012)

        self.__client_id_validated = True
        self.__client_id = new_client_id

    def can_assume_client_id(self, assumed_client_id):
        if self.__client_id_validated:
            return self.client_id == '*' or self.client_id == assumed_client_id
        elif self.client_id is None or self.client_id == '*':
            return True  # client ID is unknown
        else:
            return self.client_id == assumed_client_id

    def _get_auth_headers(self):
        if self.__auth_mechanism == Auth.Method.BASIC:
            return {
                'Authorization': 'Basic %s' % self.basic_credentials,
            }
        else:
            self.__authorize_when_necessary()
            return {
                'Authorization': 'Bearer %s' % self.token_credentials,
            }

    def _timestamp(self):
        """Returns the local time in milliseconds since the unix epoch"""
        return int(time.time() * 1000)

    def _random_nonce(self):
        return uuid.uuid4().hex[:16]

    def token_request_from_auth_url(self, method, url, token_params,
                                    headers, auth_params):
        if method == 'GET':
            body = {}
            params = dict(auth_params, **token_params)
        elif method == 'POST':
            params = {}
            body = dict(auth_params, **token_params)

        from ably.http.http import Response
        response = Response(requests.request(
            method, url, headers=headers, params=params, data=body))

        AblyException.raise_for_response(response)
        try:
            token_request = response.to_native()
        except ValueError:
            token_request = response.text
        return token_request
