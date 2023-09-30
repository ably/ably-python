import logging
from methoddispatch import SingleDispatch, singledispatch

from ably.executer.decorator import force_sync
from ably.types.message import Message
from ably.util.exceptions import catch_all
from ably.rest.channel import Channel

log = logging.getLogger(__name__)


class ChannelSync(SingleDispatch, Channel):
    @force_sync
    @catch_all
    async def history(self, direction=None, limit: int = None, start=None, end=None):
        """Returns the history for this channel"""
        return await super().history(direction, limit, start, end)

    @singledispatch
    def _publish(self, arg, *args, **kwargs):
        raise TypeError('Unexpected type %s' % type(arg))

    @force_sync
    @_publish.register(Message)
    async def publish_message(self, message, params=None, timeout=None):
        return await super().publish_message(message, params, timeout)

    @force_sync
    @_publish.register(list)
    async def publish_messages(self, messages, params=None, timeout=None):
        return await super().publish_messages(messages, params, timeout)

    @force_sync
    @_publish.register(str)
    async def publish_name_data(self, name, data, timeout=None):
        return await super().publish_name_data(name, data, timeout)

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
