from __future__ import absolute_import

import base64
import json
import time

from ably.util.exceptions import catch_all
from ably.types.message import Message


class Channel(object):
    def __init__(self, rest, name):
        self.__rest = rest
        self.__name = name

    @catch_all
    def presence(self, params=None, timeout=None):
        """Returns the presence for this channel"""
        params = params or {}
        path = '/channels/%s/presence' % self.__name
        return self.__rest._get(path, params=params, timeout=timeout).json()

    @catch_all
    def history(self, params=None, timeout=None):
        """Returns the history for this channel"""
        params = params or {}
        path = '/channels/%s/history' % self.__name
        messages = self.__rest._get(path, params=params, timeout=timeout).json()
        return [Message(m) for m in messages]

    @catch_all
    def publish(self, name, data, timeout=None, encoding=None):
        """Publishes a message on this channel.

        :Parameters:
        - `name`: the name for this message
        - `data`: the data for this message
        """

        message = Message(name, data)

        if self.ably.encrypted:
            message.encrypt(self.cipher)

        if self.ably.use_text_protocol:
            request_body = message.as_json()
        else:
            request_body = message.as_thrift()

        path = '/channels/%s/publish' % self.__name
        return self.__rest._post(path, data=request_body, timeout=timeout).json()


class Channels(object):
    def __init__(self, rest):
        self.__rest = rest
        self.__attached = {}

    def get(self, name):
        name = unicode(name)
        if name not in self.__attached:
            self.__attached[name] = Channel(self.__rest, name)
        return self.__attached[name]

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, name):
        try:
            return getattr(super(Channels, self), name)
        except AttributeError:
            return self.get(name)
