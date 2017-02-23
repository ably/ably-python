from __future__ import absolute_import

from datetime import datetime, timedelta

from six.moves.urllib.parse import urlencode

from ably.http.paginatedresult import PaginatedResult
from ably.types.mixins import EncodeDataMixin


def _ms_since_epoch(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds() * 1000)


def _dt_from_ms_epoch(ms):
    epoch = datetime.utcfromtimestamp(0)
    return epoch + timedelta(milliseconds=ms)


class PresenceAction(object):
    ABSENT = 0
    PRESENT = 1
    ENTER = 2
    LEAVE = 3
    UPDATE = 4


class PresenceMessage(EncodeDataMixin):
    def __init__(self, id=None, action=None, client_id=None,
                 data=None, encoding=None, connection_id=None,
                 timestamp=None):
        self.__id = id
        self.__action = action
        self.__client_id = client_id
        self.__connection_id = connection_id
        self.__data = data
        self.__encoding = encoding
        self.__timestamp = timestamp

    @staticmethod
    def from_encoded(obj, cipher=None):
        id = obj.get('id')
        action = obj.get('action', PresenceAction.ENTER)
        client_id = obj.get('clientId')
        connection_id = obj.get('connectionId')

        encoding = obj.get('encoding', '')
        timestamp = obj.get('timestamp')

        if timestamp is not None:
            timestamp = _dt_from_ms_epoch(timestamp)

        data = obj.get('data')

        decoded_data = PresenceMessage.decode(data, encoding, cipher)

        return PresenceMessage(
            id=id,
            action=action,
            client_id=client_id,
            connection_id=connection_id,
            timestamp=timestamp,
            **decoded_data
        )

    @property
    def action(self):
        return self.__action

    @property
    def client_id(self):
        return self.__client_id

    @property
    def encoding(self):
        return self.__encoding

    @property
    def member_key(self):
        if self.connection_id and self.client_id:
            return "%s:%s" % (self.connection_id, self.client_id)

    @property
    def data(self):
        return self.__data

    @property
    def id(self):
        return self.__id

    @property
    def connection_id(self):
        return self.__connection_id

    @property
    def timestamp(self):
        return self.__timestamp


class Presence(object):
    def __init__(self, channel):
        self.__base_path = channel.base_path
        self.__binary = channel.ably.options.use_binary_protocol
        self.__http = channel.ably.http
        self.__cipher = channel.cipher

    def _path_with_qs(self, rel_path, qs=None):
        path = rel_path
        if qs:
            path += ('?' + urlencode(qs))
        return path

    def get(self, limit=None):
        qs = {}
        if limit:
            if limit > 1000:
                raise ValueError("The maximum allowed limit is 1000")
            qs['limit'] = limit
        path = self._path_with_qs('%s/presence' % self.__base_path.rstrip('/'), qs)

        if self.__cipher:
            presence_handler = make_encrypted_presence_response_handler(self.__cipher, self.__binary)
        else:
            presence_handler = make_presence_response_handler(self.__binary)

        return PaginatedResult.paginated_query(
            self.__http, url=path, response_processor=presence_handler)

    def history(self, limit=None, direction=None, start=None, end=None):
        qs = {}
        if limit:
            if limit > 1000:
                raise ValueError("The maximum allowed limit is 1000")
            qs['limit'] = limit
        if direction:
            qs['direction'] = direction
        if start:
            if isinstance(start, int):
                qs['start'] = start
            else:
                qs['start'] = _ms_since_epoch(start)
        if end:
            if isinstance(end, int):
                qs['end'] = end
            else:
                qs['end'] = _ms_since_epoch(end)

        if 'start' in qs and 'end' in qs and qs['start'] > qs['end']:
            raise ValueError("'end' parameter has to be greater than or equal to 'start'")

        path = self._path_with_qs('%s/presence/history' % self.__base_path.rstrip('/'), qs)

        if self.__cipher:
            presence_handler = make_encrypted_presence_response_handler(
                self.__cipher, self.__binary)
        else:
            presence_handler = make_presence_response_handler(self.__binary)

        return PaginatedResult.paginated_query(
            self.__http, url=path, response_processor=presence_handler)

def make_presence_response_handler(binary):
    def presence_response_handler(response):
        messages = response.to_native()
        return PresenceMessage.from_encoded_array(messages)
    return presence_response_handler


def make_encrypted_presence_response_handler(cipher, binary):
    def encrypted_presence_response_handler(response):
        messages = response.to_native()
        return PresenceMessage.from_encoded_array(messages, cipher=cipher)
    return encrypted_presence_response_handler
