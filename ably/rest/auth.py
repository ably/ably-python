from __future__ import absolute_import

import base64
import hashlib
import hmac
import json
import logging
import random
import time

import six
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
        self._token_details = None
        self.__auth_method = Auth.Method.BASIC
        useToken = self.shouldUseTokenAuth()
        if options and options.keyValue is not None:
            # We have the key, no need to authenticate the client
            # default to using basic auth
            log.debug("anonymous, using basic auth")
            
            basic_key = "%s:%s" % (options.keyId, options.keyValue)
            basic_key = base64.b64encode(basic_key.encode('utf-8'))
            self.__basic_credentials = basic_key.decode('ascii')
        elif not options.auth_token and not useToken:
            raise AblyException(reason="Neither Token auth nor Basic auth can be setup. Provide a key, or a token, or the means to request a token.",
                                status_code=400,
                                code=40000)
        
        if useToken:
            # Using token auth
            self.__auth_method = Auth.Method.TOKEN

            if options.auth_token:
                self._token_details = TokenDetails(id=options.auth_token)
            else:
                self._token_details = None

            if options.auth_callback:
                log.debug("using token auth with auth_callback")
            elif options.auth_url:
                log.debug("using token auth with auth_url")
            elif options.keyValue:
                log.debug("using token auth with client-side signing")
            elif options.auth_token:
                log.debug("using token auth with supplied token only")
            else:
                # Not a hard error, but any operation requiring authentication
                # will fail
                log.debug("no authentication parameters supplied")


    def can_request_token(self):
      if options.keyId and options.keyValue:
          return True
      if options.authUrl:
          return True
      if options.auth_callback:
         return True
      return False
      
    def shouldUseTokenAuth(self):
        return self.__auth_options.useTokenAuth or self.__auth_options.clientId or self.__auth_options.authUrl or self.__auth_options.auth_callback 


    def authorise(self, force=False, **kwargs):
        if self._token_details:
            if self._token_details.expires > self._timestamp():
                if not force:
                    log.debug(
                        "using cached token; expires = %d",
                        self._token_details.expires
                    )
                    return self._token_details
            else:
                # token has expired
                self._token_details = None

        self._token_details = self.requestToken(**kwargs)
        return self._token_details

    def requestToken(self, keyId=None, keyValue=None, query_time=None,
                      auth_token=None, auth_callback=None, auth_url=None,
                      auth_headers=None, auth_params=None, token_params=None):
        print ("requesting token...")

        keyId = keyId or self.auth_options.keyId
        keyValue = keyValue or self.auth_options.keyValue

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

        token_params.setdefault("clientId", self.ably.clientId)
        token_params.setdefault("capability", self.ably.options.capability)
        if self.ably.options.ttl:
            token_params.setdefault("ttl", self.ably.options.ttl)

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
        elif keyValue:
            log.debug("using token auth with client-side signing " + str(token_params))
            signed_token_request = self.create_token_request(
                keyId=keyId,
                keyValue=keyValue,
                query_time=query_time,
                token_params=token_params)
        else:
            log.debug('No auth_callback, auth_url or keyValue specified')
            raise AblyException(
                "Auth.requestToken() must include valid auth parameters",
                400,
                40000)

        token_path = "/keys/%s/requestToken" % keyId
        response = self.ably.http.post(
            token_path,
            headers=auth_headers,
            body=signed_token_request,
            skip_auth=True
        )

        AblyException.raise_for_response(response)
        #access_token = response.json()["token"]
        #log.debug("Token: %s" % str(access_token))

        if not response.error:
            return TokenDetails.from_dict(response.json())
        else:
            print("TODO handle this error ... " + response.error.message)
            return TokenDetails()

    def create_token_request(self, keyId=None, keyValue=None,
                             query_time=False, token_params=None):
        token_params = token_params or {}

        if token_params.setdefault("id", keyId) != keyId:
            raise AblyException("Incompatible key specified", 401, 40102)

        if not keyId or not keyValue:
            log.debug('keyId or keyValue blank')
            raise AblyException("No key specified", 401, 40101)

        if not token_params.get("timestamp"):
            if query_time:
                token_params["timestamp"] = self.ably.time()
            else:
                token_params["timestamp"] = self._timestamp()

        token_params["timestamp"] = int(token_params["timestamp"])

        if token_params.get("capability") is None:
            token_params["capability"] = ""

        if token_params.get("clientId") is None:
            token_params["clientId"] = ""

        if isinstance(token_params["clientId"], str):
            token_params["clientId"] = unicode(token_params["clientId"], "utf-8")

        if not token_params.get("nonce"):
            # Note: There is no expectation that the client
            # specifies the nonce; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes
            token_params["nonce"] = self._random()



        if not token_params.get("ttl"):
            token_params["ttl"] =  3600000

        theId = token_params["id"].encode("utf-8")
        theTtl = str(token_params["ttl"]).encode("utf-8")
        theCapability =token_params["capability"].encode('utf-8')
        theClientId = token_params["clientId"].encode('utf-8')
        theTimestamp = str(token_params["timestamp"]).encode('utf-8')
        theNonce = token_params["nonce"].encode('utf-8')
           
        req = {
            "keyName": theId,
            "capability": theCapability,
            "clientId": theClientId,
            "timestamp": theTimestamp,
            "nonce": theNonce,
            "ttl" : theTtl
        }

        if not token_params.get("mac"):
            # Note: There is no expectation that the client
            # specifies the mac; this is done by the library
            # However, this can be overridden by the client
            # simply for testing purposes.

            sign_text = '%s\n%s\n%s\n%s\n%s\n%s\n' % (theId, theTtl, theCapability, theClientId, theTimestamp, theNonce)
            keyValue = keyValue.encode('utf-8')
            
            sign_text = sign_text.encode('utf-8')
            log.debug("Key value: '%s'" % keyValue)
            log.debug("Sign text: '%s'" % sign_text)

            mac = hmac.new(keyValue, sign_text, hashlib.sha256).digest()
            mac = base64.b64encode(mac)
            token_params["mac"] = mac

        req["mac"] = token_params.get("mac")

        signed_request = json.dumps(req)
        log.debug("generated signed request: '%s'", signed_request)

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
                'Authorization': 'Bearer %s' % self.authorise().id,
            }

    def _timestamp(self):
        """Returns the local time in seconds since the unix epoch"""
        return int(time.time()*1000)

    def _random(self):
        return "%016d" % rnd.randint(0, 9999999999999999)
