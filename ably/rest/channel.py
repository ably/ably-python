from __future__ import absolute_import

import base64
from collections import OrderedDict
import logging
import json
import os

import six
import msgpack
from six.moves.urllib import parse

from ably.http.paginatedresult import PaginatedResult, format_params
from ably.types.message import Message, make_message_response_handler
from ably.types.presence import Presence
from ably.util.crypto import get_cipher
from ably.util.exceptions import catch_all, IncompatibleClientIdException

log = logging.getLogger(__name__)


class Channel(object):
    def __init__(self, ably, name, options):
        self.__ably = ably
        self.__name = name
        self.__base_path = '/channels/%s/' % parse.quote_plus(name, safe=':')
        self.__cipher = None
        self.options = options
        self.__presence = Presence(self)

    @catch_all
    def history(self, direction=None, limit=None, start=None, end=None, timeout=None):
        """Returns the history for this channel"""
        params = format_params({}, direction=direction, start=start, end=end, limit=limit)
        path = self.__base_path + 'messages' + params

        message_handler = make_message_response_handler(self.__cipher)
        return PaginatedResult.paginated_query(
            self.ably.http, url=path, response_processor=message_handler)

    def __publish_request_body(self, name=None, data=None, client_id=None,
                               extras=None, messages=None):
        """
        Helper private method, separated from publish() to test RSL1j
        """
        if not messages:
            messages = [Message(name, data, client_id, extras=extras)]

        # Idempotent publishing
        if self.ably.options.idempotent_rest_publishing:
            # RSL1k1
            if all(message.id is None for message in messages):
                base_id = base64.b64encode(os.urandom(12)).decode()
                for serial, message in enumerate(messages):
                    message.id = u'{}:{}'.format(base_id, serial)

        request_body_list = []
        for m in messages:
            if m.client_id == '*':
                raise IncompatibleClientIdException(
                    'Wildcard client_id is reserved and cannot be used when publishing messages',
                    400, 40012)
            elif m.client_id is not None and not self.ably.auth.can_assume_client_id(m.client_id):
                raise IncompatibleClientIdException(
                    'Cannot publish with client_id \'{}\' as it is incompatible with the '
                    'current configured client_id \'{}\''.format(m.client_id, self.ably.auth.client_id),
                    400, 40012)

            if self.cipher:
                m.encrypt(self.__cipher)

            request_body_list.append(m)

        request_body = [
            message.as_dict(binary=self.ably.options.use_binary_protocol)
            for message in request_body_list]

        if len(request_body) == 1:
            request_body = request_body[0]

        return request_body

    def publish(self, name=None, data=None, client_id=None, extras=None,
                messages=None, timeout=None):
        """Publishes a message on this channel.

        :Parameters:
        - `name`: the name for this message.
        - `data`: the data for this message.
        - `messages`: list of `Message` objects to be published.
            Specify this param OR `name` and `data`.

        :attention: You can publish using `name` and `data` OR `messages`, never all three.
        """
        request_body = self.__publish_request_body(name, data, client_id, extras, messages)

        if not self.ably.options.use_binary_protocol:
            request_body = json.dumps(request_body, separators=(',', ':'))
        else:
            request_body = msgpack.packb(request_body, use_bin_type=True)

        path = self.__base_path + 'messages'
        return self.ably.http.post(path, body=request_body, timeout=timeout)

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
    def options(self):
        return self.__options

    @property
    def presence(self):
        return self.__presence

    @options.setter
    def options(self, options):
        self.__options = options

        if options and 'cipher' in options:
            cipher = options.get('cipher')
            if cipher is not None:
                cipher = get_cipher(cipher)
            self.__cipher = cipher


class Channels(object):
    def __init__(self, rest):
        self.__ably = rest
        self.__attached = OrderedDict()

    def get(self, name, **kwargs):
        if isinstance(name, six.binary_type):
            name = name.decode('ascii')

        if name not in self.__attached:
            result = self.__attached[name] = Channel(self.__ably, name, kwargs)
        else:
            result = self.__attached[name]
            if len(kwargs) != 0:
                result.options = kwargs

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
