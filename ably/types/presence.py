from __future__ import absolute_import

import base64
from datetime import datetime, timedelta

import six
from six.moves.urllib.parse import urlencode

from ably.http.httputils import HttpUtils
from ably.http.paginatedresult import PaginatedResult


def _ms_since_epoch(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds() * 1000)


def _dt_from_ms_epoch(ms):
    epoch = datetime.utcfromtimestamp(0)
    return  epoch + timedelta(milliseconds=ms)


class PresenceAction(object):
    ABSENT = 0
    PRESENT = 1
    ENTER = 2
    LEAVE = 3
    UPDATE = 4


class PresenceMessage(object):
    def __init__(self, id=None, action=None, client_id=None,
                 member_key=None, data=None, encoding=None,
                 connection_id=None, timestamp=None):
        self.__id = id
        self.__action = action
        self.__client_id = client_id
        self.__connection_id = connection_id
        if member_key is None:
            self.__member_key = "%s:%s" % (self.connection_id, self.client_id)
        else:
            self.__member_key = member_key
        self.__data = data
        self.__encoding = encoding
        self.__timestamp = timestamp

    @staticmethod
    def from_dict(obj):
        id = obj.get('id')
        action = obj.get('action', PresenceAction.ENTER)
        client_id = obj.get('clientId')
        member_key = obj.get('memberKey')
        connection_id = obj.get('connectionId')

        encoding = obj.get('encoding')
        data = obj.get('data')
        if data and 'base64' == encoding:
            data = base64.b64decode(data)

        timestamp = obj.get('timestamp')
        if timestamp is not None:
            timestamp = _dt_from_ms_epoch(timestamp)
        return PresenceMessage(
            id=id,
            action=action,
            client_id=client_id,
            member_key=member_key,
            data=data,
            connection_id=connection_id,
            encoding=encoding,
            timestamp=timestamp
        )

    @staticmethod
    def messages_from_array(obj):
        return [PresenceMessage.from_dict(d) for d in obj]

    def to_dict(self):
        if self.action is None:
            raise KeyError('action is missing or invalid, cannot generate a valid Hash for ProtocolMessage')
        obj = {
            'action': self.action,
        }

        if self.client_id is not None:
            obj['clientId'] = self.client_id

        if self.encoding is not None:
            obj['encoding'] = self.encoding

        if self.member_key is not None:
            obj['memberKey'] = self.member_key

        if self.connection_id is not None:
            obj['connectionId'] = self.connection_id

        if self.data is not None:
            if isinstance(self.data, six.byte_type) and obj['encoding'] == 'base64':
                obj['clientData'] = base64.b64encode(self.data)
            else:
                obj['clientData'] = self.data

        if self.id is not None:
            obj['id'] = self.id

        if self.timestamp is not None:
            obj['timestamp'] = _ms_since_epoch(self.timestamp)

        return obj

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
        return self.__member_key

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
        self.__binary = not channel.ably.options.use_text_protocol
        self.__http = channel.ably.http

    def _path_with_qs(self, rel_path, qs=None):
        path = rel_path
        if qs:
            path += ('?' + urlencode(qs))
        return path

    def get(self, limit=None):
        qs = {}
        if limit:
            qs['limit'] = min(limit, 1000)
        path = self._path_with_qs('%s/presence' % self.__base_path.rstrip('/'), qs)
        headers = HttpUtils.default_get_headers(self.__binary)
        return PaginatedResult.paginated_query(
            self.__http,
            path,
            headers,
            presence_response_handler)

    def history(self, limit=None, direction=None, start=None, end=None):
        qs = {}
        if limit:
            qs['limit'] = min(limit, 1000)
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
        headers = HttpUtils.default_get_headers(self.__binary)
        return PaginatedResult.paginated_query(
            self.__http,
            path,
            headers,
            presence_response_handler
        )


def presence_response_handler(response):
    return [PresenceMessage.from_dict(presence) for presence in response.json()]
