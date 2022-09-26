import asyncio
from ably.realtime.connection import ConnectionState
from unittest.mock import Mock
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestEventEmitter(BaseAsyncTestCase):
    async def setUp(self):
        self.test_vars = await RestSetup.get_test_vars()

    async def test_connection_events(self):
        realtime = await RestSetup.get_ably_realtime()
        listener = Mock()
        realtime.connection.add_listener(ConnectionState.CONNECTED, listener)

        await realtime.connect()

        # Listener is only called once event loop is free
        listener.assert_not_called()
        await asyncio.sleep(0)
        listener.assert_called_once()
        await realtime.close()

    async def test_event_listener_error(self):
        realtime = await RestSetup.get_ably_realtime()
        listener = Mock()

        # If a listener throws an exception it should not propagate (#RTE6)
        listener.side_effect = Exception()
        realtime.connection.add_listener(ConnectionState.CONNECTED, listener)

        await realtime.connect()

        listener.assert_not_called()
        await asyncio.sleep(0)
        listener.assert_called_once()
        await realtime.close()

    async def test_event_emitter_off(self):
        realtime = await RestSetup.get_ably_realtime()
        listener = Mock()
        realtime.connection.add_listener(ConnectionState.CONNECTED, listener)
        realtime.connection.remove_listener(ConnectionState.CONNECTED, listener)

        await realtime.connect()

        listener.assert_not_called()
        await asyncio.sleep(0)
        listener.assert_not_called()
        await realtime.close()
