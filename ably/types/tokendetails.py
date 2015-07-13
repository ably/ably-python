from __future__ import absolute_import

import six
import base64

from ably.types.capability import Capability


class TokenDetails(object):
    def __init__(self, id=None, expires=0, issued_at=0,
                 capability=None, clientId=None):
        self.__id = id
        self._expires = expires #can be set with _expires for testing
        self.__issued_at = issued_at
        self.__capability = capability
        self.__clientId = clientId

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        self.__id = id

    @property
    def expires(self):
        return self._expires



    @property
    def issued_at(self):
        return self.__issued_at

    @property
    def capability(self):
        return self.__capability

    @property
    def clientId(self):
        return self.__clientId

    @staticmethod
    def from_dict(obj):
        return TokenDetails(
            id=base64.b64encode(obj.get("token")),
            expires=int(obj.get("expires", 0)),
            issued_at=int(obj.get("issued", 0)),
            capability=obj.get("capability"),
            clientId=obj.get("clientId")
        )
