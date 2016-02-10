from __future__ import absolute_import

import json
import time

import six

from ably.types.capability import Capability


class TokenDetails(object):

    DEFAULTS = {'ttl': 60 * 60 * 1000}
    # Buffer in milliseconds before a token is considered unusable
    # For example, if buffer is 10000ms, the token can no longer be used for
    # new requests 9000ms before it expires
    TOKEN_EXPIRY_BUFFER = 15 * 1000

    def __init__(self, token=None, expires=None, issued=0,
                 capability=None, client_id=None):
        if expires is None:
            self.__expires = time.time() * 1000 + TokenDetails.DEFAULTS['ttl']
        else:
            self.__expires = expires
        self.__token = token
        self.__issued = issued
        if capability and isinstance(capability, six.string_types):
            self.__capability = Capability(json.loads(capability))
        else:
            self.__capability = Capability(capability or {})
        self.__client_id = client_id

    @property
    def token(self):
        return self.__token

    @property
    def expires(self):
        return self.__expires

    @property
    def issued(self):
        return self.__issued

    @property
    def capability(self):
        return self.__capability

    @property
    def client_id(self):
        return self.__client_id

    def is_expired(self, timestamp):
        if self.__expires is None:
            return False
        else:
            return self.__expires < timestamp + self.TOKEN_EXPIRY_BUFFER

    @staticmethod
    def from_dict(obj):
        kwargs = {
            'token': obj.get("token"),
            'capability': obj.get("capability"),
            'client_id': obj.get("clientId")
        }
        expires = obj.get("expires")
        kwargs['expires'] = expires if expires is None else int(expires)
        issued = obj.get("issued")
        kwargs['issued'] = issued if issued is None else int(issued)

        return TokenDetails(**kwargs)
