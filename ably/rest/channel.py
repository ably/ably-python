from __future__ import absolute_import

import calendar
import logging
import json
from collections import OrderedDict

import six
from six.moves.urllib.parse import urlencode, quote

from ably.http.httputils import HttpUtils
from ably.http.paginatedresult import PaginatedResult
from ably.types.message import (
    Message, message_response_handler, make_encrypted_message_response_handler,
    MessageJSONEncoder)
from ably.types.presence import Presence
from ably.util.crypto import get_cipher
from ably.util.exceptions import catch_all

log = logging.getLogger(__name__)


class Channel(object):
    def __init__(self, ably, name, options):
        self.__ably = ably
        self.__name = name
        self.__base_path = '/channels/%s/' % quote(name)
        self.__presence = Presence(self)
        self.options = options

    def _format_time_param(self, t):
        try:
            return '%d' % (calendar.timegm(t.utctimetuple()) * 1000)
        except:
            return '%s' % t

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
    def publish(self, name=None, data=None, messages=None, timeout=None):
        """Publishes a message on this channel.

        :Parameters:
        - `name`: the name for this message.
        - `data`: the data for this message.
        - `messages`: list of `Message` objects to be published.
            Specify this param OR `name` and `data`.

        :attention: You can publish using `name` and `data` OR `messages`, never all three.
        """
        if not messages:
            messages = [Message(name, data)]

        # TODO: messagepack
        if not self.ably.options.use_text_protocol:
            raise NotImplementedError

        request_body_list = []
        for m in messages:
            if self.encrypted:
                m.encrypt(self.__cipher)

            request_body_list.append(m)

        if len(request_body_list) == 1:
            request_body = request_body_list[0].as_json()
        else:
            request_body = json.dumps(request_body_list, cls=MessageJSONEncoder)

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
    def name(self):
        return self.__name

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

    @property
    def presence(self):
        return self.__presence

    @options.setter
    def options(self, options):
        self.__options = options

        if options and options.encrypted:
            self.__cipher = get_cipher(options.cipher_params)
        else:
            self.__cipher = None


class Channels(object):
    def __init__(self, rest):
        self.__ably = rest
        self.__attached = OrderedDict()

    def get(self, name, options=None):
        if isinstance(name, six.binary_type):
            name = name.decode('ascii')

        if name not in self.__attached:
            result = self.__attached[name] = Channel(self.__ably, name, options)
        else:
            result = self.__attached[name]
            if options is not None:
                result.options = options

        return result

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, name):
        try:
            return getattr(super(Channels, self), name)
        except AttributeError:
            return self.get(name)

    def __contains__(self, item):
        if isinstance(item, Channel):
            name = item.name
        elif isinstance(item, six.binary_type):
            name = item.decode('ascii')
        else:
            name = item

        return name in self.__attached

    def __iter__(self):
        return iter(six.itervalues(self.__attached))

    def release(self, key):
        del self.__attached[key]

    def __delitem__(self, key):
        return self.release(key)
