from __future__ import absolute_import

import base64

import six

class PresenceAction(object):
    ENTER = 0
    LEAVE = 1
    UPDATE = 2
    

class PresenceMessage(object):
    def __init__(self, action=PresenceAction.ENTER, client_id=None, member_id=None,
            client_data=None):
        self.__action = action
        self.__client_id = client_id
        self.__member_id = member_id
        self.__client_data = client_data

    @staticmethod
    def from_dict(obj):
        action = obj.get('action', PresenceAction.ENTER)
        client_id = obj.get('clientId')
        member_id = obj.get('memberId')

        encoding = obj.get('encoding')
        client_data = obj.get('clientData')
        if client_data and 'base64' == encoding:
            client_data = base64.b64decode(client_data)

        return PresenceMessage(action=action, client_id=client_id, 
                member_id=member_id, client_data=client_data)

        
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
            # TODO b64 encode data if necessary
            obj['clientData'] = self.client_data

        if self.member_id is not None:
            obj['memberId'] = self.member_id

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

def presence_response_handler(response):
    # TODO implement
    pass
