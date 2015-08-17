from __future__ import absolute_import

import base64
from datetime import datetime

import six
from six.moves.urllib.parse import urlencode

from ably.http.httputils import HttpUtils
from ably.http.paginatedresult import PaginatedResult


class PresenceAction(object):
    ENTER = 0
    LEAVE = 1
    UPDATE = 2


class PresenceMessage(object):
    def __init__(self, action=PresenceAction.ENTER, client_id=None,
                 member_id=None, client_data=None, message_id=None,
                 connection_id=None, timestamp=None):
        self.__action = action
        self.__client_id = client_id
        self.__member_id = member_id
        self.__message_id = message_id
        self.__client_data = client_data
        self.__connection_id = connection_id
        self.__timestamp = timestamp

    @staticmethod
    def from_dict(obj):
        action = obj.get('action', PresenceAction.ENTER)
        client_id = obj.get('clientId')
        message_id = obj.get('id')
        connection_id = obj.get('connectionId')
        timestamp = obj.get('timestamp')

        encoding = obj.get('encoding')
        client_data = obj.get('data')
        if client_data and 'base64' == encoding:
            client_data = base64.b64decode(client_data)

        return PresenceMessage(
            action=action,
            client_id=client_id,
            message_id=message_id,
            client_data=client_data,
            connection_id=connection_id,
            timestamp=timestamp
        )

    @staticmethod
    def messages_from_array(obj):
        return [PresenceMessage.from_dict(d) for d in obj]

    def to_dict(self):
        obj = {
            'action': self.action,
        }

        if self.client_id is not None:
            obj['clientId'] = self.client_id

        if self.client_data is not None:
            if isinstance(self.client_data, six.byte_type):
                obj['clientData'] = base64.b64encode(self.client_data)
                obj['encoding'] = 'base64'
            else:
                obj['clientData'] = self.client_data

        if self.member_id is not None:
            obj['memberId'] = self.member_id

        if self.message_id is not None:
            obj['id'] = self.message_id

        return obj

    @property
    def action(self):
        return self.__action

    @property
    def client_id(self):
        return self.__client_id

    @property
    def client_data(self):
        return self.__client_data

    @property
    def member_id(self):
        return self.__member_id

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

    def _ms_since_epoch(self, dt):
        epoch = datetime.utcfromtimestamp(0)
        delta = dt - epoch
        return int(delta.total_seconds() * 1000)

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
                qs['start'] = self._ms_since_epoch(start)
        if end:
            if isinstance(end, int):
                qs['end'] = end
            else:
                qs['end'] = self._ms_since_epoch(end)

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
