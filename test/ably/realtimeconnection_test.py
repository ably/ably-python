import asyncio
from ably.realtime.connection import ConnectionState, ProtocolMessageAction
import pytest
from ably.util.exceptions import AblyAuthException, AblyException
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeAuth(BaseAsyncTestCase):
    async def setUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.valid_key_format = "api:key"

    async def test_auth_connection(self):
        ably = await RestSetup.get_ably_realtime(auto_connect=False)
        assert ably.connection.state == ConnectionState.INITIALIZED
        await ably.connect()
        assert ably.connection.state == ConnectionState.CONNECTED
        await ably.close()
        assert ably.connection.state == ConnectionState.CLOSED

    async def test_connecting_state(self):
        ably = await RestSetup.get_ably_realtime()
        task = asyncio.create_task(ably.connect())
        await asyncio.sleep(0)
        assert ably.connection.state == ConnectionState.CONNECTING
        await task
        await ably.close()

    async def test_closing_state(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        task = asyncio.create_task(ably.close())
        await asyncio.sleep(0)
        assert ably.connection.state == ConnectionState.CLOSING
        await task

    async def test_auth_invalid_key(self):
        ably = await RestSetup.get_ably_realtime(key=self.valid_key_format)
        with pytest.raises(AblyAuthException) as exception:
            await ably.connect()
        assert ably.connection.state == ConnectionState.FAILED
        assert ably.connection.error_reason == exception.value
        await ably.close()

    async def test_connection_ping_connected(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert type(response_time_ms) is float
        await ably.close()

    async def test_connection_ping_initialized(self):
        ably = await RestSetup.get_ably_realtime(auto_connect=False)
        assert ably.connection.state == ConnectionState.INITIALIZED
        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000

    async def test_connection_ping_failed(self):
        ably = await RestSetup.get_ably_realtime(key=self.valid_key_format)
        with pytest.raises(AblyAuthException) as exception:
            await ably.connect()
        assert ably.connection.state == ConnectionState.FAILED
        assert ably.connection.error_reason == exception.value
        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000
        await ably.close()

    async def test_connection_ping_closed(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        assert ably.connection.state == ConnectionState.CONNECTED
        await ably.close()
        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000

    async def test_auto_connect(self):
        ably = await RestSetup.get_ably_realtime()
        connect_future = asyncio.Future()
        ably.connection.on(ConnectionState.CONNECTED, lambda change: connect_future.set_result(change))
        await connect_future
        assert ably.connection.state == ConnectionState.CONNECTED
        await ably.close()

    async def test_connection_state_change(self):
        ably = await RestSetup.get_ably_realtime()

        connected_future = asyncio.Future()

        def on_state_change(change):
            connected_future.set_result(change)

        ably.connection.on(ConnectionState.CONNECTED, on_state_change)

        state_change = await connected_future
        assert state_change.previous == ConnectionState.CONNECTING
        assert state_change.current == ConnectionState.CONNECTED
        await ably.close()

    async def test_connection_state_change_reason(self):
        ably = await RestSetup.get_ably_realtime(key=self.valid_key_format)

        failed_changes = []

        def on_state_change(change):
            failed_changes.append(change)

        ably.connection.on(ConnectionState.FAILED, on_state_change)

        with pytest.raises(AblyAuthException) as exception:
            await ably.connect()

        print('connect returned')

        assert len(failed_changes) == 1
        state_change = failed_changes[0]
        assert state_change is not None
        assert state_change.previous == ConnectionState.CONNECTING
        assert state_change.current == ConnectionState.FAILED
        assert state_change.reason == exception.value
        assert ably.connection.error_reason == exception.value
        await ably.close()

    async def test_realtime_request_timeout_connect(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=0.000001)
        with pytest.raises(AblyException) as exception:
            await ably.connect()
        assert exception.value.code == 50003
        assert exception.value.status_code == 504
        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert ably.connection.error_reason == exception.value
        await ably.close()

    async def test_realtime_request_timeout_ping(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connect()
        original_send_protocol_message = ably.connection.connection_manager.send_protocol_message

        async def new_send_protocol_message(msg):
            if msg.get('action') == ProtocolMessageAction.HEARTBEAT:
                return
            await original_send_protocol_message(msg)
        ably.connection.connection_manager.send_protocol_message = new_send_protocol_message

        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 50003
        assert exception.value.status_code == 504
        await ably.close()

    async def test_realtime_request_timeout_close(self):
        ably = await RestSetup.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connect()

        async def new_close_transport():
            pass

        ably.connection.connection_manager.transport.close = new_close_transport

        with pytest.raises(AblyException) as exception:
            await ably.close()
        assert exception.value.code == 50003
        assert exception.value.status_code == 504
