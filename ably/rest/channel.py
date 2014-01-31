from __future__ import absolute_import

import base64
import json
import time
import urllib

import six

from ably.http.httputils import HttpUtils
from ably.http.paginatedresult import PaginatedResult
from ably.types.message import Message
from ably.types.presence import PresenceMessage, presence_response_handler
from ably.util.exceptions import catch_all


class Presence(object):
    def __init__(self, channel):
        self.__base_path = channel.base_path
        self.__binary = not channel.ably.options.use_text_protocol
        self.__http = channel.ably.http

    def get(self):
        path = '%s/presence' % self.__base_path
        headers = HttpUtils.default_get_headers(self.__binary)
        response = self.__http.get(path, headers=headers)
        return presence_response_handler(response)

    def history(self):
        path = '%s/presence/history' % self.__base_path
        headers = HttpUtils.default_get_headers(self.__binary)
        response = self.__http.get(path, headers=headers)
        return PaginatedResult.paginated_query(self.__http, path, headers, presence_response_handler)


class Channel(object):
    def __init__(self, ably, name, options):
        self.__ably = ably
        self.__name = name
        self.__options = options
        self.__base_path = '/channels/%s/' % urllib.quote(name)
        self.__presence = Presence()

        if options and options.encrypted:
            self.__cipher = Crypto.get_cipher(options)
        else:
            self.__cipher = None

    @catch_all
    def presence(self, params=None, timeout=None):
        """Returns the presence for this channel"""
        params = params or {}
        path = '/channels/%s/presence' % self.__name
        return self.__ably._get(path, params=params, timeout=timeout).json()

    @catch_all
    def history(self, params=None, timeout=None):
        """Returns the history for this channel"""
        params = params or {}
        path = '/channels/%s/history' % self.__name

        if params:
            path = path + '?' + urllib.urlencode(params)

        return PaginatedResult.paginated_query(self.ably.http, path, None, messages_processor)

    @catch_all
    def publish(self, name, data, timeout=None, encoding=None):
        """Publishes a message on this channel.

        :Parameters:
        - `name`: the name for this message
        - `data`: the data for this message
        """

        message = Message(name, data)

        if self.encrypted:
            message.encrypt(self.__cipher)

        if self.ably.use_text_protocol:
            request_body = message.as_json()
        else:
            request_body = message.as_thrift()

        path = '/channels/%s/publish' % self.__name
        return self.__ably._post(path, data=request_body, timeout=timeout).json()

    @property
    def ably(self):
        return self.__ably

    @property
    def base_path(self):
        return self.__base_path

    @property
    def cipher(self):
        return self.__cipher

    @property
    def encrypted(self):
        return self.options and self.options.encrypted

    @property
    def options(self):
        return self.__options


class Channels(object):
    def __init__(self, rest):
        self.__ably = rest
        self.__attached = {}

    def get(self, name):
        if isinstance(name, six.binary_type):
            name = name.decode('ascii')
        if name not in self.__attached:
            self.__attached[name] = Channel(self.__ably, name)
        return self.__attached[name]

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, name):
        try:
            return getattr(super(Channels, self), name)
        except AttributeError:
            return self.get(name)
