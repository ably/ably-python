import logging

from ably.executer.decorator import force_sync
from ably.rest.channel import Channel
from collections import OrderedDict
from typing import Iterator
from ably.util.exceptions import catch_all

log = logging.getLogger(__name__)


class ChannelSync(Channel):
    @force_sync
    @catch_all
    async def history(self, direction=None, limit: int = None, start=None, end=None):
        """Returns the history for this channel"""
        return await super().history(direction, limit, start, end)

    @force_sync
    async def publish(self, *args, **kwargs):
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
        return await super().publish(args, kwargs)

    @force_sync
    async def status(self):
        """Retrieves current channel active status with no. of publishers, subscribers, presence_members etc"""

        return await super().status()


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
