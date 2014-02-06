from __future__ import absolute_import

import base64
import hashlib
import hmac
import json
import logging
import random
import time
import types

import requests

from ably.types.capability import Capability
from ably.types.tokendetails import TokenDetails

# initialise and seed our own instance of random
rnd = random.Random()
rnd.seed()

from ably.util.exceptions import AblyException

__all__ = ["Auth"]

log = logging.getLogger(__name__)


class TokenDetails(object):
    def __init__(self):
        self.__id = None
        self.__expires = 0
        self.__issued_at = 0
        self.__capability = None
        self.__client_id = None

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, v):
        self.__id = v

    @property
    def expires(self):
        return self.__expires

    @expires.setter
    def expires(self, v):
        self.__expires = v

    @property
    def issued_at(self):
        return self.__issued_at

    @issued_at.setter
    def issued_at(self, v):
        self.__issued_at = v

    @property
    def capability(self):
        return self.__capability

    @capability.setter
    def capability(self, v):
        self.__capability = v

    @property
    def client_id(self):
        return self.__client_id

    @client_id.setter
    def client_id(self, v):
        self.__client_id = v


class Auth(object):
    class Method:
        BASIC = "BASIC"
        TOKEN = "TOKEN"

    def __init__(self, ably, options):
        self.__ably = ably
        self.__auth_options = options

        self.__basic_credentials = None
        self.__token_credentials = None
        self.__auth_params = None
        self.__token_details = None

        if options.key_value is not None and options.client_id is None:
            # We have the key, no need to authenticate the client
            # default to using basic auth
            log.info("anonymous, using basic auth")
            self.__auth_method = Auth.Method.BASIC
            basic_key = "%s:%s" % (options.key_id, options.key_value)
            basic_key = base64.b64encode(basic_key.encode('utf-8'))
            self.__basic_credentials = basic_key.decode('ascii')
            return

        # Using token auth
        self.__auth_method = Auth.Method.TOKEN

        if options.auth_token:
            self.__token_details = TokenDetails()
            self.__token_details.id = options.auth_token
        else:
            self.__token_details = None

        if options.auth_callback:
            log.info("using token auth with auth_callback")
        elif auth_url:
            log.info("using token auth with auth_url")
        elif key_value:
            log.info("using token auth with client-side signing")
        elif auth_token:
            log.info("using token auth with supplied token only")
        else:
            # Not a hard error, but any operation requiring authentication
            # will fail
            log.info("no authentication parameters supplied")

    def authorise(self, force=False, **kwargs):
        if self.__token_details:
            if self.__token_details.expires > self._timestamp():
                if not force:
                    log.info("using cached token; expires = %d" %
                             self.__token_details.expires)
                    return self.__token_details
            else:
                # token has expired
                self.__token_details = None

        self.__token_details = self.request_token(**kwargs)
        return self.__token_details

    def request_token(self, key_id=None, key_value=None, query_time=None,
                      auth_token=None, auth_callback=None, auth_url=None,
                      auth_headers=None, auth_params=None, token_params=None):
        key_id = key_id or self.auth_options.key_id
        key_value = key_value or self.auth_options.key_value

        log.debug('key_id: %s' % key_id)
        log.debug('key_value: %s' % key_value)

        query_time = bool(query_time)
        auth_token = auth_token or self.auth_options.auth_token
        auth_callback = auth_callback or self.auth_options.auth_callback
        auth_url = auth_url or self.auth_options.auth_url
        auth_headers = auth_headers or {
            "Content-Encoding": "utf-8",
            "Content-Type": "application/json",
        }
        auth_params = auth_params or self.auth_params

        token_params = token_params or TokenParams()

        if token_params.client_id is None:
            token_params.client_id = self.ably.client_id

        signed_token_request = ""
        if auth_callback:
            log.info("using token auth with authCallback")
            signed_token_request = auth_callback(token_params)
        elif auth_url:
            log.info("using token auth with authUrl")
            response = requests.post(auth_url,
                                     headers=auth_headers,
                                     params=auth_params,
                                     data=token_params.as_json())

            AblyException.raise_for_response(response)

            signed_token_request = response.text
        elif key_value:
            log.info("using token auth with client-side signing")
            signed_token_request = self.create_token_request(
                key_id=key_id,
                key_value=key_value,
                query_time=query_time,
                token_params=token_params)
        else:
            log.debug('No auth_callback, auth_url or key_value specified')
            raise AblyException(
                "Auth.request_token() must include valid auth parameters",
                400,
                40000)

        token_path = "/keys/%s/requestToken" % key_id
        log.info("TokenPath: %s" % token_path)
        log.info("Headers: %s" % str(auth_headers))
        log.info("Params: %s" % str(auth_params))
        log.info("Body: %s" % signed_token_request)
        response = requests.post(
            token_path,
            headers=auth_headers,
            params=auth_params,
            data=signed_token_request)

        AblyException.raise_for_response(response)

        access_token = response.json()["access_token"]
        log.debug("Token: %s" % str(access_token))
        return TokenDetails.from_json(access_token)

    def create_token_request(self, key_id=None, key_value=None,
                             query_time=False, token_params=None):
        token_params = token_params or {}

        if token_params.setdefault("id", key_id) != key_id:
            raise AblyException("Incompatible key specified", 401, 40102)

        if not key_id or not key_value:
            log.debug('key_id or key_value blank')
            raise AblyException("No key specified", 401, 40101)

        if not token_params.get("timestamp"):
            if query_time:
                token_params["timestamp"] = self.__rest.time() / 1000.0
            else:
                token_params["timestamp"] = self._timestamp()

        token_params["timestamp"] = int(token_params["timestamp"])

        if not token_params.get("nonce"):
            # Note: There is no expectation that the client
            # specifies the nonce; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes
            token_params["nonce"] = self._random()

        req = {
            "id": key_id,
            "capability": token_params.get("capability", ""),
            "client_id": token_params.get("client_id", self.__rest.client_id),
            "timestamp": token_params["timestamp"],
            "nonce": token_params["nonce"]
        }

        if token_params.get("ttl"):
            req["ttl"] = token_params["ttl"]

        if not token_params.get("mac"):
            # Note: There is no expectation that the client
            # specifies the mac; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes.
            sign_text = "\n".join([str(x) for x in [
                token_params["id"],
                token_params.get("ttl", ""),
                token_params.get("capability", ""),
                token_params.get("client_id", ""),
                "%d" % token_params["timestamp"],
                token_params.get("nonce", ""),
                "",  # to get the trailing new line
            ]])

            mac = hmac.new(str(key_value), sign_text, hashlib.sha256).digest()
            mac = base64.b64encode(mac)
            log.info("Key: %s" % key_value)
            log.info("Plaintext: %s" % sign_text)
            token_params["mac"] = mac
            log.info("Token Params: %s" % str(token_params))

        req["mac"] = token_params.get("mac")

        signed_request = json.dumps(req)
        log.info("generated signed request: %s", signed_request)

        return signed_request

    @property
    def ably(self):
        return self.__ably

    @property
    def auth_method(self):
        return self.__auth_method

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
        return self.__token_credentials

    def _get_auth_headers(self):
        if self.__auth_method == Auth.Method.BASIC:
            return {
                'Authorization': 'Basic %s' % self.__basic_credentials,
            }
        else:
            return {
                'Authorization': 'Bearer %s' % self.authorise()["id"],
            }

    def _timestamp(self):
        """Returns the local time in seconds since the unix epoch"""
        return int(time.time())

    def _random(self):
        return "%016d" % rnd.randint(0, 9999999999999999)
