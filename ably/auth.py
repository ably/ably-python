import base64
import hashlib
import hmac
import json
import logging
import random
import time
import types

import requests

# initialise and seed our own instance of random
rnd = random.Random()
rnd.seed()

from ably.exceptions import AblyException

__all__ = ["Auth"]

log = logging.getLogger(__name__)


def c14n(capability):
    '''Canonicalizes the capability'''
    if not capability:
        return ''

    if isinstance(capability, types.StringTypes):
        capability = json.loads(capability)

    if not capability:
        return ''

    c14n_capability = {}

    for key in capability.keys():
        c14n_capability[key] = sorted(capability[key])

    return json.dumps(c14n_capability)


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

    def __init__(self, rest, key_id=None, key_value=None,
                 auth_token=None, auth_callback=None, auth_url=None,
                 auth_headers=None, auth_params=None, client_id=None):
        self.__rest = rest
        self.__key_id = key_id
        self.__key_value = key_value
        self.__auth_token = auth_token
        self.__auth_callback = auth_callback
        self.__auth_url = auth_url
        self.__auth_headers = auth_headers
        self.__auth_params = auth_params

        if key_value is not None:
            if not client_id:
                # We have the key, no need to authenticate the client
                # default to using basic auth
                log.info("anonymous, using basic auth")
                self.__auth_method = Auth.Method.BASIC
                basic_key = "%s:%s" % (key_id, key_value)
                basic_key = base64.b64encode(basic_key)
                self.__basic_credentials = basic_key
                return

        # Using token auth
        self.__auth_method = Auth.Method.TOKEN

        if auth_token:
            self.__token_details = TokenDetails()
            self.__token_details.id = auth_token
        else:
            self.__token_details = None

        if auth_callback:
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
        key_id = key_id or self.__key_id
        key_value = key_value or self.__key_value
        query_time = bool(query_time)
        auth_token = auth_token or self.__auth_token
        auth_callback = auth_callback or self.__auth_callback
        auth_url = auth_url or self.__auth_url
        auth_headers = auth_headers or self.__auth_headers
        auth_params = auth_params or self.__auth_params

        token_params = token_params or {}

        token_params.setdefault("client_id", self.__rest.client_id)

        if "capability" in token_params:
            token_params["capability"] = c14n(token_params["capability"])

        signed_token_request = ""
        if auth_callback:
            log.info("using token auth with authCallback")
            signed_token_request = auth_callback(token_params)
        elif auth_url:
            log.info("using token auth with authUrl")
            response = requests.post(auth_url,
                                     headers=auth_headers,
                                     params=auth_params,
                                     data=json.dumps(token_params))

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
            raise AblyException(
                "Auth.request_token() must include valid auth parameters",
                400,
                40000)

        token_path = "%s/keys/%s/requestToken" % (self.__rest.base_uri, key_id)
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

        return response.json()["access_token"]

    def create_token_request(self, key_id=None, key_value=None,
                             query_time=False, token_params=None):
        token_params = token_params or {}

        if token_params.setdefault("id", key_id) != key_id:
            raise AblyException("Incompatible key specified", 401, 40102)

        if not key_id or not key_value:
            raise AblyException("No key specified", 401, 40101)

        if not token_params.get("timestamp"):
            if query_time:
                token_params["timestamp"] = self.__rest.time()
            else:
                token_params["timestamp"] = self._timestamp()

        req = {
            "id": key_id,
            "capability": token_params.get("capability", ""),
            "client_id": token_params.get("client_id", self.__rest.client_id),
            "timestamp": token_params["timestamp"],
            "nonce": token_params.get("nonce") or self._random(),
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
                "%d" % token_params.get("timestamp", ""),
                token_params.get("nonce", ""),
                "",  # to get the trailing new line
            ]])

            log.info("Key: %s" % key_value)
            log.info("Plaintext: %s" % sign_text)
            mac = hmac.new(str(key_value), sign_text, hashlib.sha256).digest()
            mac = base64.b64encode(mac)
            token_params["mac"] = mac

        req["mac"] = token_params.get("mac")

        log.info("generated signed request")

        return json.dumps(req)

    @property
    def auth_method(self):
        return self.__auth_method

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
        """Returns the local time in ms since the unix epoch"""
        return time.time() * 1000.0

    def _random(self):
        return "%016d" % rnd.randint(0, 9999999999999999)
