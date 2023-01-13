import asyncio
from ably.realtime.connection import ConnectionEvent, ConnectionState, ProtocolMessageAction
import pytest
from ably.util.exceptions import AblyAuthException, AblyException
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase
from ably.transport.defaults import Defaults


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

    async def test_disconnected_retry_timeout(self):
        ably = await RestSetup.get_ably_realtime(disconnected_retry_timeout=2000, auto_connect=False)
        original_connect = ably.connection.connection_manager._connect
        call_count = 0
        test_future = asyncio.Future()
        test_exception = Exception()

        # intercept the library connection mechanism to fail the first two connection attempts
        async def new_connect():
            nonlocal call_count
            if call_count < 2:
                call_count += 1
                raise test_exception
            else:
                await original_connect()
                test_future.set_result(None)

        ably.connection.connection_manager._connect = new_connect

        with pytest.raises(Exception) as exception:
            await ably.connect()

        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert exception.value == test_exception

        await test_future

        assert ably.connection.state == ConnectionState.CONNECTED

        await ably.close()

    async def test_unroutable_host(self):
        ably = await RestSetup.get_ably_realtime(realtime_host="10.255.255.1")
        with pytest.raises(AblyException) as exception:
            await ably.connect()
        assert exception.value.code == 50003
        assert exception.value.status_code == 504
        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert ably.connection.error_reason == exception.value
        await ably.close()

    async def test_invalid_host(self):
        ably = await RestSetup.get_ably_realtime(realtime_host="iamnotahost")
        with pytest.raises(AblyException) as exception:
            await ably.connect()
        assert exception.value.code == 40000
        assert exception.value.status_code == 400
        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert ably.connection.error_reason == exception.value
        await ably.close()

    async def test_connection_state_ttl(self):
        Defaults.connection_state_ttl = 100
        ably = await RestSetup.get_ably_realtime(realtime_host="iamnotahost")
        changes = []
        suspended_future = asyncio.Future()

        def on_state_change(state_change):
            changes.append(state_change)
            if state_change.current == ConnectionState.SUSPENDED:
                suspended_future.set_result(None)
        with pytest.raises(AblyException) as exception:
            await ably.connect()
        ably.connection.on(on_state_change)
        assert exception.value.code == 40000
        assert exception.value.status_code == 400
        assert ably.connection.state == ConnectionState.DISCONNECTED
        await suspended_future
        assert ably.connection.state == changes[-1].current
        assert ably.connection.state == ConnectionState.SUSPENDED
        assert ably.connection.connection_details is None
        assert ably.connection.error_reason == changes[-1].reason
        await ably.close()
        Defaults.connection_state_ttl = 120000

    async def test_handle_connected(self):
        ably = await RestSetup.get_ably_realtime()
        test_future = asyncio.Future()

        def on_update(connection_state):
            if connection_state.event == ConnectionEvent.UPDATE:
                test_future.set_result(connection_state)

        ably.connection.on(ConnectionEvent.UPDATE, on_update)
        await ably.connection.connection_manager.on_protocol_message({'action': 4, "connectionDetails":
                                                                      {"connectionStateTtl": 200}})
        state_change = await test_future

        assert state_change.previous == ConnectionState.CONNECTED
        assert state_change.current == ConnectionState.CONNECTED
        assert state_change.event == ConnectionEvent.UPDATE
        await ably.close()
