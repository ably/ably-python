from __future__ import absolute_import

from ably.types.capability import Capability


class TokenDetails(object):
    def __init__(self, id=None, expires=0, issued_at=0,
                 capability=None, client_id=None):
        self.__id = id
        self.__expires = expires
        self.__issued_at = issued_at
        self.__capability = Capability(capability or {})
        self.__client_id = client_id

    @property
    def id(self):
        return self.__id

    @property
    def expires(self):
        return self.__expires

    @property
    def issued_at(self):
        return self.__issued_at

    @property
    def capability(self):
        return self.__capability

    @property
    def client_id(self):
        return self.__client_id

    @staticmethod
    def from_dict(obj):
        return TokenDetails(
            id=obj.get("id"),
            expires=int(obj.get("expires", 0)),
            issued_at=int(obj.get("issued_at", 0)),
            capability=obj.get("capability"),
            client_id=obj.get("clientId")
        )
