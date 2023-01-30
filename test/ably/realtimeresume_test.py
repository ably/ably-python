from ably.realtime.connection import ConnectionState
from ably.realtime.realtime_channel import ChannelState
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase, random_string


class TestRealtimeResume(BaseAsyncTestCase):
    async def asyncSetUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.valid_key_format = "api:key"

    # RTN15c6 - valid resume response
    async def test_connection_resume(self):
        ably = await RestSetup.get_ably_realtime()

        await ably.connection.once_async(ConnectionState.CONNECTED)
        prev_connection_id = ably.connection.connection_manager.connection_id
        connection_key = ably.connection.connection_details.connection_key
        await ably.connection.connection_manager.transport.dispose()
        ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)

        await ably.connection.once_async(ConnectionState.CONNECTED)
        new_connection_id = ably.connection.connection_manager.connection_id
        assert ably.connection.connection_manager.transport.params["resume"] == connection_key
        assert prev_connection_id == new_connection_id

        await ably.close()

    # RTN15c4 - fatal resume error
    async def test_fatal_resume_error(self):
        ably = await RestSetup.get_ably_realtime()

        await ably.connection.once_async(ConnectionState.CONNECTED)
        key_name = ably.options.key_name
        ably.key = f"{key_name}:wrong-secret"
        await ably.connection.connection_manager.transport.dispose()
        ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)

        state_change = await ably.connection.once_async(ConnectionState.FAILED)
        assert state_change.reason.code == 40101
        assert state_change.reason.status_code == 401
        await ably.close()

    # RTN15c7 - invalid resume response
    async def test_invalid_resume_response(self):
        ably = await RestSetup.get_ably_realtime()

        await ably.connection.once_async(ConnectionState.CONNECTED)

        assert ably.connection.connection_manager.connection_details
        ably.connection.connection_manager.connection_details.connection_key = 'ably-python-fake-key'

        assert ably.connection.connection_manager.transport
        await ably.connection.connection_manager.transport.dispose()
        ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)

        state_change = await ably.connection.once_async(ConnectionState.CONNECTED)

        assert state_change.reason.code == 80018
        assert state_change.reason.status_code == 400
        assert ably.connection.error_reason == state_change.reason

        await ably.close()

    async def test_attached_channel_reattaches_on_invalid_resume(self):
        ably = await RestSetup.get_ably_realtime()

        await ably.connection.once_async(ConnectionState.CONNECTED)

        channel = ably.channels.get(random_string(5))

        await channel.attach()

        assert ably.connection.connection_manager.connection_details
        ably.connection.connection_manager.connection_details.connection_key = 'ably-python-fake-key'

        assert ably.connection.connection_manager.transport
        await ably.connection.connection_manager.transport.dispose()
        ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)

        await ably.connection.once_async(ConnectionState.CONNECTED)

        assert channel.state == ChannelState.ATTACHING

        await channel.once_async(ChannelState.ATTACHED)

        await ably.close()

    async def test_suspended_channel_reattaches_on_invalid_resume(self):
        ably = await RestSetup.get_ably_realtime()

        await ably.connection.once_async(ConnectionState.CONNECTED)

        channel = ably.channels.get(random_string(5))
        channel.state = ChannelState.SUSPENDED

        assert ably.connection.connection_manager.connection_details
        ably.connection.connection_manager.connection_details.connection_key = 'ably-python-fake-key'

        assert ably.connection.connection_manager.transport
        await ably.connection.connection_manager.transport.dispose()
        ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)

        await ably.connection.once_async(ConnectionState.CONNECTED)

        assert channel.state == ChannelState.ATTACHING

        await channel.once_async(ChannelState.ATTACHED)

        await ably.close()
