from __future__ import absolute_import

import base64
import json

import six


class PresenceAction(object):
    ENTER = 0
    LEAVE = 1
    UPDATE = 2


class PresenceMessage(object):
    def __init__(self, action, client_id=None,
                 client_data=None, member_id=None):
        self.__action = action
        self.__client_id = client_id
        self.__client_data = client_data
        self.__member_id = None

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

    @staticmethod
    def from_dict(obj):
        pm = PresenceMessage()
        pm.action = obj.get('action', 0)
        pm.client_id = obj.get('clientId', '')
        pm.member_id = obj.get('memberId', '')
        encoding = obj.get('encoding', '')
        client_data = obj.get('clientData', '')

        if 'base64' == encoding:
            pm.client_data = base64.b64decode(client_data)
        else:
            pm.client_data = client_data

        return pm

    @staticmethod
    def from_json(jsonstr):
        obj = json.loads(jsonstr)

        if isinstance(obj, dict):
            return PresenceMessage.from_obj(obj)
        elif isinstance(obj, list):
            return [PresenceMessage.from_obj(i) for i in obj]
        else:
            raise ValueError('Invalid presence message str')

    def to_dict(self):
        d = {
            "action": self.action,
        }
        if self.client_id is not None:
            d["clientId"] = self.client_id

        if self.client_data is not None:
            if isinstance(self.client_data, six.byte_type):
                d['clientData'] = base64.b64encode(self.client_data)
                d['encoding'] = 'base64'
            else:
                d['clientData'] = self.client_data
        return d

    def to_json(self):
        return json.dumps(self.to_dict())
