import asyncio
from unittest.mock import Mock
import types
from ably.realtime.realtime_channel import ChannelState
from ably.types.message import Message
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeChannel(BaseAsyncTestCase):
    async def setUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.valid_key_format = "api:key"

    async def test_channels_get(self):
        ably = await RestSetup.get_ably_realtime()
        channel = ably.channels.get('my_channel')
        assert channel == ably.channels.all['my_channel']
        await ably.close()

    async def test_channels_release(self):
        ably = await RestSetup.get_ably_realtime()
        ably.channels.get('my_channel')
        ably.channels.release('my_channel')
        assert ably.channels.all.get('my_channel') is None
        await ably.close()

    async def test_channel_attach(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        channel = ably.channels.get('my_channel')
        assert channel.state == ChannelState.INITIALIZED
        await channel.attach()
        assert channel.state == ChannelState.ATTACHED
        await ably.close()

    async def test_channel_detach(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        channel = ably.channels.get('my_channel')
        await channel.attach()
        await channel.detach()
        assert channel.state == ChannelState.DETACHED
        await ably.close()

    # RTL7b
    async def test_subscribe(self):
        ably = await RestSetup.get_ably_realtime()

        first_message_future = asyncio.Future()
        second_message_future = asyncio.Future()

        def listener(message):
            if not first_message_future.done():
                first_message_future.set_result(message)
            else:
                second_message_future.set_result(message)

        await ably.connect()
        channel = ably.channels.get('my_channel')
        await channel.attach()
        await channel.subscribe('event', listener)

        # publish a message using rest client
        rest = await RestSetup.get_ably_rest()
        rest_channel = rest.channels.get('my_channel')
        await rest_channel.publish('event', 'data')
        message = await first_message_future

        assert isinstance(message, Message)
        assert message.name == 'event'
        assert message.data == 'data'

        # test that the listener is called again for further publishes
        await rest_channel.publish('event', 'data')
        await second_message_future

        await ably.close()
        await rest.close()

    async def test_subscribe_coroutine(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        channel = ably.channels.get('my_channel')
        await channel.attach()

        message_future = asyncio.Future()

        # AsyncMock doesn't work in python 3.7 so use an actual coroutine
        async def listener(msg):
            message_future.set_result(msg)

        await channel.subscribe('event', listener)

        # publish a message using rest client
        rest = await RestSetup.get_ably_rest()
        rest_channel = rest.channels.get('my_channel')
        await rest_channel.publish('event', 'data')

        message = await message_future
        assert isinstance(message, Message)
        assert message.name == 'event'
        assert message.data == 'data'

        await ably.close()
        await rest.close()

    # RTL7a
    async def test_subscribe_all_events(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        channel = ably.channels.get('my_channel')
        await channel.attach()

        message_future = asyncio.Future()
        listener = Mock(spec=types.FunctionType, side_effect=lambda msg: message_future.set_result(msg))
        await channel.subscribe(listener)

        # publish a message using rest client
        rest = await RestSetup.get_ably_rest()
        rest_channel = rest.channels.get('my_channel')
        await rest_channel.publish('event', 'data')
        message = await message_future

        listener.assert_called_once()
        assert isinstance(message, Message)
        assert message.name == 'event'
        assert message.data == 'data'

        await ably.close()
        await rest.close()

    # RTL7c
    async def test_subscribe_auto_attach(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        channel = ably.channels.get('my_channel')
        assert channel.state == ChannelState.INITIALIZED

        listener = Mock()
        await channel.subscribe('event', listener)

        assert channel.state == ChannelState.ATTACHED

        await ably.close()
