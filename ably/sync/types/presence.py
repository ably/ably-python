from datetime import datetime, timedelta
from urllib import parse

from ably.sync.http.paginatedresult import PaginatedResultSync
from ably.sync.types.mixins import EncodeDataMixin


def _ms_since_epoch(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds() * 1000)


def _dt_from_ms_epoch(ms):
    epoch = datetime.utcfromtimestamp(0)
    return epoch + timedelta(milliseconds=ms)


class PresenceAction:
    ABSENT = 0
    PRESENT = 1
    ENTER = 2
    LEAVE = 3
    UPDATE = 4


class PresenceMessage(EncodeDataMixin):

    def __init__(self,
                 id=None,  # TP3a
                 action=None,  # TP3b
                 client_id=None,  # TP3c
                 connection_id=None,  # TP3d
                 data=None,  # TP3e
                 encoding=None,  # TP3f
                 timestamp=None,  # TP3g
                 member_key=None,  # TP3h (for RT only)
                 extras=None,  # TP3i (functionality not specified)
                 ):

        self.__id = id
        self.__action = action
        self.__client_id = client_id
        self.__connection_id = connection_id
        self.__data = data
        self.__encoding = encoding
        self.__timestamp = timestamp
        self.__member_key = member_key
        self.__extras = extras

    @property
    def id(self):
        return self.__id

    @property
    def action(self):
        return self.__action

    @property
    def client_id(self):
        return self.__client_id

    @property
    def connection_id(self):
        return self.__connection_id

    @property
    def data(self):
        return self.__data

    @property
    def encoding(self):
        return self.__encoding

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def member_key(self):
        if self.connection_id and self.client_id:
            return "%s:%s" % (self.connection_id, self.client_id)

    @property
    def extras(self):
        return self.__extras

    @staticmethod
    def from_encoded(obj, cipher=None):
        id = obj.get('id')
        action = obj.get('action', PresenceAction.ENTER)
        client_id = obj.get('clientId')
        connection_id = obj.get('connectionId')
        data = obj.get('data')
        encoding = obj.get('encoding', '')
        timestamp = obj.get('timestamp')
        # member_key = obj.get('memberKey', None)
        extras = obj.get('extras', None)

        if timestamp is not None:
            timestamp = _dt_from_ms_epoch(timestamp)

        decoded_data = PresenceMessage.decode(data, encoding, cipher)

        return PresenceMessage(
            id=id,
            action=action,
            client_id=client_id,
            connection_id=connection_id,
            timestamp=timestamp,
            extras=extras,
            **decoded_data
        )


class Presence:
    def __init__(self, channel):
        self.__base_path = '/channels/%s/' % parse.quote_plus(channel.name)
        self.__binary = channel.ably.options.use_binary_protocol
        self.__http = channel.ably.http
        self.__cipher = channel.cipher

    def _path_with_qs(self, rel_path, qs=None):
        path = rel_path
        if qs:
            path += ('?' + parse.urlencode(qs))
        return path

    def get(self, limit=None):
        qs = {}
        if limit:
            if limit > 1000:
                raise ValueError("The maximum allowed limit is 1000")
            qs['limit'] = limit
        path = self._path_with_qs(self.__base_path + 'presence', qs)

        presence_handler = make_presence_response_handler(self.__cipher)
        return PaginatedResultSync.paginated_query(
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

        path = self._path_with_qs(self.__base_path + 'presence/history', qs)

        presence_handler = make_presence_response_handler(self.__cipher)
        return PaginatedResultSync.paginated_query(
            self.__http, url=path, response_processor=presence_handler)


def make_presence_response_handler(cipher):
    def encrypted_presence_response_handler(response):
        messages = response.to_native()
        return PresenceMessage.from_encoded_array(messages, cipher=cipher)
    return encrypted_presence_response_handler
