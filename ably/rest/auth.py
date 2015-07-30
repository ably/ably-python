from __future__ import absolute_import

import base64
import hashlib
import hmac
import json
import logging
import random
import time

import six

from ably.types.capability import Capability
from ably.types.tokendetails import TokenDetails

# initialise and seed our own instance of random
rnd = random.Random()
rnd.seed()

from ably.util.exceptions import AblyException

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
        self.__token_credentials = None
        self.__auth_params = None
        self.__token_details = None

        if options.key_value is not None and options.client_id is None:
            # We have the key, no need to authenticate the client
            # default to using basic auth
            log.debug("anonymous, using basic auth")
            self.__auth_method = Auth.Method.BASIC
            basic_key = "%s:%s" % (options.key_id, options.key_value)
            basic_key = base64.b64encode(basic_key.encode('utf-8'))
            self.__basic_credentials = basic_key.decode('ascii')
            return

        # Using token auth
        self.__auth_method = Auth.Method.TOKEN

        if options.auth_token:
            self.__token_details = TokenDetails(token=options.auth_token)
        else:
            self.__token_details = None

        if options.auth_callback:
            log.debug("using token auth with auth_callback")
        elif options.auth_url:
            log.debug("using token auth with auth_url")
        elif options.key_value:
            log.debug("using token auth with client-side signing")
        elif options.auth_token:
            log.debug("using token auth with supplied token only")
        else:
            # Not a hard error, but any operation requiring authentication
            # will fail
            log.debug("no authentication parameters supplied")

    def authorise(self, force=False, **kwargs):
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

    def request_token(self, key_id=None, key_value=None, query_time=None,
                      auth_token=None, auth_callback=None, auth_url=None,
                      auth_headers=None, auth_params=None, token_params=None):
        key_id = key_id or self.auth_options.key_id
        key_value = key_value or self.auth_options.key_value

        log.debug("Auth callback: %s" % auth_callback)
        log.debug("Auth options: %s" % six.text_type(self.auth_options))
        query_time = bool(query_time)
        auth_token = auth_token or self.auth_options.auth_token
        auth_callback = auth_callback or self.auth_options.auth_callback
        auth_url = auth_url or self.auth_options.auth_url
        auth_headers = auth_headers or {
            "Content-Encoding": "utf-8",
            "Content-Type": "application/json",
        }
        auth_params = auth_params or self.auth_params

        token_params = token_params or {}

        token_params.setdefault("client_id", self.ably.client_id)

        signed_token_request = ""

        log.debug("Token Params: %s" % token_params)
        if auth_callback:
            log.debug("using token auth with authCallback")
            signed_token_request = auth_callback(**token_params)
        elif auth_url:
            log.debug("using token auth with authUrl")
            response = self.ably.http.post(
                auth_url,
                headers=auth_headers,
                body=json.dumps(token_params),
                skip_auth=True
            )

            AblyException.raise_for_response(response)

            signed_token_request = response.text
        elif key_value:
            log.debug("using token auth with client-side signing")
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
        response = self.ably.http.post(
            token_path,
            headers=auth_headers,
            body=signed_token_request,
            skip_auth=True
        )

        AblyException.raise_for_response(response)
        response_json = response.json()
        log.debug("Token: %s" % str(response_json.get("token")))
        return TokenDetails.from_dict(response_json)

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
                token_params["timestamp"] = self.ably.time()
            else:
                token_params["timestamp"] = self._timestamp()

        token_params["timestamp"] = int(token_params["timestamp"])

        if token_params.get("capability") is None:
            token_params["capability"] = ""
        else:
            token_params['capability'] = six.text_type(
                Capability(token_params["capability"])
            )

        if token_params.get("client_id") is None:
            token_params["client_id"] = ""

        if not token_params.get("nonce"):
            # Note: There is no expectation that the client
            # specifies the nonce; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes
            token_params["nonce"] = self._random()

        req = {
            "keyName": key_id,
            "capability": token_params["capability"],
            "client_id": token_params["client_id"],
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
            sign_text = six.u("\n").join([six.text_type(x) for x in [
                token_params["id"],
                token_params.get("ttl", ""),
                token_params["capability"],
                token_params["client_id"],
                "%d" % token_params["timestamp"],
                token_params.get("nonce", ""),
                "",  # to get the trailing new line
            ]])
            key_value = key_value.encode('utf8')
            sign_text = sign_text.encode('utf8')
            log.debug("Key value: %s" % key_value)
            log.debug("Sign text: %s" % sign_text)

            mac = hmac.new(key_value, sign_text, hashlib.sha256).digest()
            mac = base64.b64encode(mac).decode('utf8')
            token_params["mac"] = mac

        req["mac"] = token_params.get("mac")

        signed_request = json.dumps(req)
        log.debug("generated signed request: %s", signed_request)

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
                'Authorization': 'Bearer %s' % self.authorise().token,
            }

    def _timestamp(self):
        """Returns the local time in milliseconds since the unix epoch"""
        return int(time.time() * 1000)

    def _random(self):
        return "%016d" % rnd.randint(0, 9999999999999999)
