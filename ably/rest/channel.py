from __future__ import absolute_import

import calendar
import logging

import six
from six.moves.urllib.parse import urlencode, quote

from ably.http.httputils import HttpUtils
from ably.http.paginatedresult import PaginatedResult
from ably.types.message import Message, message_response_handler, make_encrypted_message_response_handler
from ably.types.presence import presence_response_handler
from ably.util.crypto import get_cipher
from ably.util.exceptions import catch_all


log = logging.getLogger(__name__)


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
        url = '/presence/history'

        headers = HttpUtils.default_get_headers(self.__binary)
        response = self.__http.get(url, headers=headers)
        # FIXME: Why response is not used here?
        return PaginatedResult.paginated_query(
            self.__http,
            url,
            headers,
            presence_response_handler
        )


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

    def _format_time_param(self, t):
        try:
            return '%d' % (calendar.timegm(t.utctimetuple()) * 1000)
        except:
            return '%s' % t

    @catch_all
    def presence(self, params=None, timeout=None):
        """Returns the presence for this channel"""
        params = params or {}
        path = '/channels/%s/presence' % self.__name
        return self.__ably._get(path, params=params, timeout=timeout).json()

    @catch_all
    def history(self, direction=None, limit=None, start=None, end=None, timeout=None):
        """Returns the history for this channel"""
        params = {}

        if direction:
            params['direction'] = '%s' % direction
        if limit:
            params['limit'] = '%d' % limit
        if start:
            params['start'] = self._format_time_param(start)
        if end:
            params['end'] = self._format_time_param(end)

        path = '/channels/%s/history' % self.__name

        if params:
            path = path + '?' + urlencode(params)

        if self.__cipher:
            message_handler = make_encrypted_message_response_handler(self.__cipher)
        else:
            message_handler = message_response_handler

        return PaginatedResult.paginated_query(
            self.ably.http,
            path,
            None,
            message_handler
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
            # TODO: messagepack
            request_body = message.as_thrift()

        path = '/channels/%s/publish' % self.__name
        headers = HttpUtils.default_post_headers(not self.ably.options.use_text_protocol)
        return self.ably.http.post(
            path,
            headers=headers,
            body=request_body,
            timeout=timeout
        ).json()

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

    def get(self, name, options=None):
        if isinstance(name, six.binary_type):
            name = name.decode('ascii')
        if name not in self.__attached:
            self.__attached[name] = Channel(self.__ably, name, options)
        return self.__attached[name]

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, name):
        try:
            return getattr(super(Channels, self), name)
        except AttributeError:
            return self.get(name)
