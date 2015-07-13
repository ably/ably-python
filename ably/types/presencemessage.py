from __future__ import absolute_import

import base64
import json

import six


class PresenceAction(object):
    ENTER = 0
    LEAVE = 1
    UPDATE = 2


class PresenceMessage(object):
    def __init__(self, action=None, clientId=None,
                 client_data=None, connection_id=None,timestamp=None):
        self.__action = action
        self.__clientId = clientId
        self.__client_data = client_data
        self.__connection_id = connection_id
        self.__timestamp = timestamp

    @property
    def action(self):
        return self.__action

    @action.setter
    def action(self, value):
        self.__action = value

    @property
    def clientId(self):
        return self.__clientId

    @clientId.setter
    def clientId(self, value):
        self.__clientId = value

    @property
    def client_data(self):
        return self.__client_data

    @client_data.setter
    def client_data(self, value):
        self.__client_data = value

    @property
    def connection_id(self):
        return self.__connection_id

    @connection_id.setter
    def connection_id(self, value):
        self.__connection_id = value

    @property
    def timestamp(self):
        return self.__timestamp

    @timestamp.setter
    def timestamp(self, value):
        self.__timestamp = value

    @staticmethod
    def from_dict(obj):

        pm = PresenceMessage()
        pm.action = obj.get('action', 0)
        pm.clientId = obj.get('clientId', '')
        pm.connection_id = obj.get('connectionId', '')

        t = obj.get('timestamp')
        if t:
            pm.timestamp = t
        encoding = obj.get('encoding', '')
        client_data = obj.get('data', '')


        if 'base64' == encoding:
            pm.client_data = base64.b64decode(client_data)
        else:
            pm.client_data = client_data

        return pm

    @staticmethod
    def from_json(jsonstr):
        obj = json.loads(jsonstr)

        if isinstance(obj, dict):
            return PresenceMessage.from_dict(obj)
        elif isinstance(obj, list):
            return [PresenceMessage.from_dict(i) for i in obj]
        else:
            raise ValueError('Invalid presence message str')

    def to_dict(self):
        d = {
            "action": self.action,
        }
        if self.clientId is not None:
            d["clientId"] = self.clientId
        if self.timestamp is not None:
            d["timestamp"] = self.timestamp

        if self.client_data is not None:
            if isinstance(self.client_data, six.byte_type):
                d['clientData'] = base64.b64encode(self.client_data)
                d['encoding'] = 'base64'
            else:
                d['clientData'] = self.client_data
        return d

    def to_json(self):
        return json.dumps(self.to_dict())

def presence_response_handler(response):
    presence_array = response.json()
    presence_objects = []
    for p in presence_array:
        presence_message = PresenceMessage.from_json(json.dumps(p))
        presence_objects.append(presence_message)
    return presence_objects
