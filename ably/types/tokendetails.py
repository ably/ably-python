from __future__ import absolute_import

import json

import six

from ably.types.capability import Capability


class TokenDetails(object):
    def __init__(self, token=None, expires=0, issued=0,
                 capability=None, client_id=None):
        self.__token = token
        self.__expires = expires
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

    @staticmethod
    def from_dict(obj):
        return TokenDetails(
            token=obj.get("token"),
            expires=int(obj.get("expires", 0)),
            issued=int(obj.get("issued", 0)),
            capability=obj.get("capability"),
            client_id=obj.get("clientId")
        )
