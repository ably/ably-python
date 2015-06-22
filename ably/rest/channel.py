from __future__ import absolute_import

import logging

import six
from six.moves.urllib.parse import urlencode, quote

from ably.http.httputils import HttpUtils
from ably.http.paginatedresult import PaginatedResult
from ably.http.http import StatusResponse
from ably.types.message import Message, message_response_handler, make_encrypted_message_response_handler
from ably.types.presencemessage import presence_response_handler
from ably.util.crypto import get_cipher
from ably.util.exceptions import catch_all



log = logging.getLogger(__name__)


class Presence(object):
    def __init__(self, channel):
        self.__base_path = channel.base_path
        self.__binary = not channel.ably.options.use_text_protocol
        self.__http = channel.ably.http

    def get(self, searchParams=None):
        url = '%spresence' % self.__base_path
        return PaginatedResult.paginated_query(self.__http,
                                                url, None,
                                                presence_response_handler,
                                                searchParams)


    def history(self, searchParams=None):
        url = '%spresence/history' % self.__base_path
        return PaginatedResult.paginated_query(self.__http,
                                                url, None,
                                                presence_response_handler,
                                                searchParams)


class Channel(object):
    def __init__(self, ably, name, options):
        self.__ably = ably
        self.__name = name
        self.__options = options
        self.__base_path = '/channels/%s/' % quote(name)
        self.__presence = Presence(self)

        if options and options.encrypted:
            self.__cipher = get_cipher(options.cipher_params)
        else:
            self.__cipher = None


    @property
    def  name(self):
        return self.__name  

    @catch_all
    def presence(self, params=None, timeout=None):
        """Returns the presence for this channel"""
        return self.__presence
        
    @catch_all
    def history(self, searchParams=None):
        """Returns the history for this channel"""

        path = '/channels/%s/history' % self.__name

        if self.__cipher:
            message_handler = make_encrypted_message_response_handler(self.__cipher)
        else:
            message_handler = message_response_handler

        return PaginatedResult.paginated_query(
            self.ably.http,
            path,
            None,
            message_handler, 
            searchParams
        )

    @catch_all
    def publish(self, name, data, timeout=None):
        """Publishes a message on this channel.

        :Parameters:
        - `name`: the name for this message
        - `data`: the data for this message
        """
        message = Message(name, data)

        if self.encrypted:
            message.encrypt(self.__cipher)

        if self.ably.options.use_text_protocol:
            request_body = message.as_json()
        else:
            print("WARN, sending as json but supposed to send as binary")
            #TODO was as_thrift
            request_body = message.as_json()

        path = '/channels/%s/publish' % self.__name
        headers = HttpUtils.default_post_headers(not self.ably.options.use_text_protocol)
        return StatusResponse(self.ably.http.post(
            path,
            headers=headers,
            body=request_body,
            timeout=timeout
        ))

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

    @options.setter
    def options(self, value):
        self.__options = value


class Channels(object):
    def __init__(self, rest):
        self.__ably = rest
        self.__attached = {}

    def get(self, name, options=None):
        if isinstance(name, six.binary_type):
            name = name.decode('ascii')
        if name not in self.__attached:
            self.__attached[name] = Channel(self.__ably, name, options)
        elif options:
            self.__attached[name].options = options
        return self.__attached[name]
        
    def names(self):
        keys = self.__attached.keys()
        keys.sort()
        return keys

    def release(self, channelName):
        if self.exists(channelName):
            self.__attached.pop(channelName)

    def exists(self, name):
        return name in self.__attached

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, name):
        try:
            return getattr(super(Channels, self), name)
        except AttributeError:
            return self.get(name)
