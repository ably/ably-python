import base64
from collections import OrderedDict
import logging
import json
import os
from typing import Iterator
from urllib import parse

from methoddispatch import SingleDispatch, singledispatch
import msgpack

from ably.sync.http.paginatedresult import PaginatedResultSync, format_params
from ably.sync.types.channeldetails import ChannelDetails
from ably.sync.types.message import Message, make_message_response_handler
from ably.sync.types.presence import Presence
from ably.sync.util.crypto import get_cipher
from ably.sync.util.exceptions import catch_all, IncompatibleClientIdException

log = logging.getLogger(__name__)


class ChannelSync(SingleDispatch):
    def __init__(self, ably, name, options):
        self.__ably = ably
        self.__name = name
        self.__base_path = '/channels/%s/' % parse.quote_plus(name, safe=':')
        self.__cipher = None
        self.options = options
        self.__presence = Presence(self)

    @catch_all
    def history(self, direction=None, limit: int = None, start=None, end=None):
        """Returns the history for this channel"""
        params = format_params({}, direction=direction, start=start, end=end, limit=limit)
        path = self.__base_path + 'messages' + params

        message_handler = make_message_response_handler(self.__cipher)
        return PaginatedResultSync.paginated_query(
            self.ably.http, url=path, response_processor=message_handler)

    def __publish_request_body(self, messages):
        """
        Helper private method, separated from publish() to test RSL1j
        """
        # Idempotent publishing
        if self.ably.options.idempotent_rest_publishing:
            # RSL1k1
            if all(message.id is None for message in messages):
                base_id = base64.b64encode(os.urandom(12)).decode()
                for serial, message in enumerate(messages):
                    message.id = '{}:{}'.format(base_id, serial)

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

    @singledispatch
    def _publish(self, arg, *args, **kwargs):
        raise TypeError('Unexpected type %s' % type(arg))

    @_publish.register(Message)
    def publish_message(self, message, params=None, timeout=None):
        return self.publish_messages([message], params, timeout=timeout)

    @_publish.register(list)
    def publish_messages(self, messages, params=None, timeout=None):
        request_body = self.__publish_request_body(messages)
        if not self.ably.options.use_binary_protocol:
            request_body = json.dumps(request_body, separators=(',', ':'))
        else:
            request_body = msgpack.packb(request_body, use_bin_type=True)

        path = self.__base_path + 'messages'
        if params:
            params = {k: str(v).lower() if type(v) is bool else v for k, v in params.items()}
            path += '?' + parse.urlencode(params)
        return self.ably.http.post(path, body=request_body, timeout=timeout)

    @_publish.register(str)
    def publish_name_data(self, name, data, timeout=None):
        messages = [Message(name, data)]
        return self.publish_messages(messages, timeout=timeout)

    def publish(self, *args, **kwargs):
        """Publishes a message on this channel.

        :Parameters:
        - `name`: the name for this message.
        - `data`: the data for this message.
        - `messages`: list of `Message` objects to be published.
        - `message`: a single `Message` objet to be published

        :attention: You can publish using `name` and `data` OR `messages` OR
        `message`, never all three.
        """
        # For backwards compatibility
        if len(args) == 0:
            if len(kwargs) == 0:
                return self.publish_name_data(None, None)

            if 'name' in kwargs or 'data' in kwargs:
                name = kwargs.pop('name', None)
                data = kwargs.pop('data', None)
                return self.publish_name_data(name, data, **kwargs)

            if 'messages' in kwargs:
                messages = kwargs.pop('messages')
                return self.publish_messages(messages, **kwargs)

        return self._publish(*args, **kwargs)

    def status(self):
        """Retrieves current channel active status with no. of publishers, subscribers, presence_members etc"""

        path = '/channels/%s' % self.name
        response = self.ably.http.get(path)
        obj = response.to_native()
        return ChannelDetails.from_dict(obj)

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


class ChannelsSync:
    def __init__(self, rest):
        self.__ably = rest
        self.__all: dict = OrderedDict()

    def get(self, name, **kwargs):
        if isinstance(name, bytes):
            name = name.decode('ascii')

        if name not in self.__all:
            result = self.__all[name] = ChannelSync(self.__ably, name, kwargs)
        else:
            result = self.__all[name]
            if len(kwargs) != 0:
                result.options = kwargs

        return result

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, name):
        return self.get(name)

    def __contains__(self, item):
        if isinstance(item, ChannelSync):
            name = item.name
        elif isinstance(item, bytes):
            name = item.decode('ascii')
        else:
            name = item

        return name in self.__all

    def __iter__(self) -> Iterator[str]:
        return iter(self.__all.values())

    # RSN4
    def release(self, name: str):
        """Releases a Channel object, deleting it, and enabling it to be garbage collected.
        If the channel does not exist, nothing happens.

        It also removes any listeners associated with the channel.

        Parameters
        ----------
        name: str
            Channel name
        """

        if name not in self.__all:
            return
        del self.__all[name]
