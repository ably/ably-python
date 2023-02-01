import asyncio
import pytest
from ably.realtime.realtime_channel import ChannelState
from ably.transport.websockettransport import ProtocolMessageAction
from ably.types.message import Message
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase, random_string
from ably.realtime.connection import ConnectionState
from ably.util.exceptions import AblyException


class TestRealtimeChannel(BaseAsyncTestCase):
    async def asyncSetUp(self):
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
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get('my_channel')
        assert channel.state == ChannelState.INITIALIZED
        await channel.attach()
        assert channel.state == ChannelState.ATTACHED
        await ably.close()

    async def test_channel_detach(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
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

        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get('my_channel')
        await channel.attach()
        await channel.subscribe('event', listener)

        # publish a message using rest client
        await channel.publish('event', 'data')
        message = await first_message_future

        assert isinstance(message, Message)
        assert message.name == 'event'
        assert message.data == 'data'

        # test that the listener is called again for further publishes
        await channel.publish('event', 'data')
        await second_message_future

        await ably.close()

    async def test_subscribe_coroutine(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
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
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get('my_channel')
        await channel.attach()

        message_future = asyncio.Future()

        def listener(msg):
            message_future.set_result(msg)

        await channel.subscribe(listener)

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

    # RTL7c
    async def test_subscribe_auto_attach(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get('my_channel')
        assert channel.state == ChannelState.INITIALIZED

        def listener(_):
            pass

        await channel.subscribe('event', listener)

        assert channel.state == ChannelState.ATTACHED

        await ably.close()

    # RTL8b
    async def test_unsubscribe(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get('my_channel')
        await channel.attach()

        message_future = asyncio.Future()
        call_count = 0

        def listener(msg):
            nonlocal call_count
            call_count += 1
            message_future.set_result(msg)

        await channel.subscribe('event', listener)

        # publish a message using rest client
        rest = await RestSetup.get_ably_rest()
        rest_channel = rest.channels.get('my_channel')
        await rest_channel.publish('event', 'data')
        await message_future
        assert call_count == 1

        # unsubscribe the listener from the channel
        channel.unsubscribe('event', listener)

        # test that the listener is not called again for further publishes
        await rest_channel.publish('event', 'data')
        await asyncio.sleep(1)
        assert call_count == 1

        await ably.close()
        await rest.close()

    # RTL8c
    async def test_unsubscribe_all(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get('my_channel')
        await channel.attach()

        message_future = asyncio.Future()
        call_count = 0

        def listener(msg):
            nonlocal call_count
            call_count += 1
            message_future.set_result(msg)

        await channel.subscribe('event', listener)

        # publish a message using rest client
        rest = await RestSetup.get_ably_rest()
        rest_channel = rest.channels.get('my_channel')
        await rest_channel.publish('event', 'data')
        await message_future
        assert call_count == 1

        # unsubscribe all listeners from the channel
        channel.unsubscribe()

        # test that the listener is not called again for further publishes
        await rest_channel.publish('event', 'data')
        await asyncio.sleep(1)
        assert call_count == 1

        await ably.close()
        await rest.close()

    async def test_realtime_request_timeout_attach(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        original_send_protocol_message = ably.connection.connection_manager.send_protocol_message

        async def new_send_protocol_message(msg):
            if msg.get('action') == ProtocolMessageAction.ATTACH:
                return
            await original_send_protocol_message(msg)
        ably.connection.connection_manager.send_protocol_message = new_send_protocol_message

        channel = ably.channels.get('channel_name')
        with pytest.raises(AblyException) as exception:
            await channel.attach()
        assert exception.value.code == 90007
        assert exception.value.status_code == 408
        await ably.close()

    async def test_realtime_request_timeout_detach(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        original_send_protocol_message = ably.connection.connection_manager.send_protocol_message

        async def new_send_protocol_message(msg):
            if msg.get('action') == ProtocolMessageAction.DETACH:
                return
            await original_send_protocol_message(msg)
        ably.connection.connection_manager.send_protocol_message = new_send_protocol_message

        channel = ably.channels.get('channel_name')
        await channel.attach()
        with pytest.raises(AblyException) as exception:
            await channel.detach()
        assert exception.value.code == 90007
        assert exception.value.status_code == 408
        await ably.close()

    async def test_channel_detached_once_connection_closed(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get(random_string(5))
        await channel.attach()

        await ably.close()
        assert channel.state == ChannelState.DETACHED

    async def test_channel_failed_once_connection_failed(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get(random_string(5))
        await channel.attach()

        ably.connection.connection_manager.notify_state(ConnectionState.SUSPENDED)
        assert channel.state == ChannelState.SUSPENDED

        await ably.close()

    async def test_channel_suspended_once_connection_suspended(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        channel = ably.channels.get(random_string(5))
        await channel.attach()

        ably.connection.connection_manager.notify_state(ConnectionState.FAILED)
        assert channel.state == ChannelState.FAILED

        await ably.close()

    async def test_attach_while_connecting(self):
        ably = await RestSetup.get_ably_realtime()
        channel = ably.channels.get(random_string(5))
        await channel.attach()
        assert channel.state == ChannelState.ATTACHED
        await ably.close()
