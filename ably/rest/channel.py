from __future__ import absolute_import

import calendar
import logging
import json
from collections import OrderedDict

import six
import msgpack
from six.moves.urllib.parse import urlencode, quote

from ably.http.paginatedresult import PaginatedResult
from ably.types.message import (
    Message, make_message_response_handler, make_encrypted_message_response_handler,
    MessageJSONEncoder)
from ably.types.presence import Presence
from ably.util.crypto import get_cipher
from ably.util.exceptions import catch_all, IncompatibleClientIdException

log = logging.getLogger(__name__)


class Channel(object):
    def __init__(self, ably, name, options):
        self.__ably = ably
        self.__name = name
        self.__base_path = '/channels/%s/' % quote(name)
        self.__cipher = None
        self.options = options
        self.__presence = Presence(self)

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
            if limit > 1000:
                raise ValueError("The maximum allowed limit is 1000")
            params['limit'] = '%d' % limit
        if start:
            params['start'] = self._format_time_param(start)
        if end:
            params['end'] = self._format_time_param(end)

        path = '/channels/%s/history' % self.__name

        if params:
            path = path + '?' + urlencode(params)

        if self.__cipher:
            message_handler = make_encrypted_message_response_handler(
                self.__cipher, self.ably.options.use_binary_protocol)
        else:
            message_handler = make_message_response_handler(
                self.ably.options.use_binary_protocol)

        return PaginatedResult.paginated_query(
            self.ably.http, url=path, response_processor=message_handler)

    @catch_all
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
        if not messages:
            messages = [Message(name, data, client_id, extras=extras)]

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

        if not self.ably.options.use_binary_protocol:
            if len(request_body_list) == 1:
                request_body = request_body_list[0].as_json()
            else:
                request_body = json.dumps(request_body_list, cls=MessageJSONEncoder)
        else:
            request_body = [message.as_dict(binary=True) for message in request_body_list]
            if len(request_body) == 1:
                request_body = request_body[0]
            request_body = msgpack.packb(request_body, use_bin_type=True)

        path = '/channels/%s/publish' % self.__name

        return self.ably.http.post(
            path,
            body=request_body,
            timeout=timeout
            )

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
            if options.get('cipher') is not None:
                self.__cipher = get_cipher(options.get('cipher'))
            else:
                self.__cipher = None


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
