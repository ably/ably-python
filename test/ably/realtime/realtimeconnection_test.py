import asyncio
from ably.realtime.connection import ConnectionEvent, ConnectionState
import pytest
from ably.transport.websockettransport import ProtocolMessageAction
from ably.util.exceptions import AblyException
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase
from ably.transport.defaults import Defaults


class TestRealtimeConnection(BaseAsyncTestCase):
    async def asyncSetUp(self):
        self.test_vars = await TestApp.get_test_vars()
        self.valid_key_format = "api:key"

    async def test_connection_state(self):
        ably = await TestApp.get_ably_realtime(auto_connect=False)
        assert ably.connection.state == ConnectionState.INITIALIZED
        ably.connect()
        await ably.connection.once_async()
        assert ably.connection.state == ConnectionState.CONNECTING
        await ably.connection.once_async()
        assert ably.connection.state == ConnectionState.CONNECTED
        await ably.close()
        assert ably.connection.state == ConnectionState.CLOSED

    async def test_connection_state_is_connecting_on_init(self):
        ably = await TestApp.get_ably_realtime()
        assert ably.connection.state == ConnectionState.CONNECTING
        await ably.close()

    async def test_auth_invalid_key(self):
        ably = await TestApp.get_ably_realtime(key=self.valid_key_format)
        state_change = await ably.connection.once_async()
        assert ably.connection.state == ConnectionState.FAILED
        assert state_change.reason
        assert state_change.reason.code == 40101
        assert state_change.reason.status_code == 401
        assert ably.connection.error_reason
        assert ably.connection.error_reason.code == 40101
        assert ably.connection.error_reason.status_code == 401
        await ably.close()

    async def test_connection_ping_connected(self):
        ably = await TestApp.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert type(response_time_ms) is float
        await ably.close()

    async def test_connection_ping_initialized(self):
        ably = await TestApp.get_ably_realtime(auto_connect=False)
        assert ably.connection.state == ConnectionState.INITIALIZED
        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000

    async def test_connection_ping_failed(self):
        ably = await TestApp.get_ably_realtime(key=self.valid_key_format)
        await ably.connection.once_async(ConnectionState.FAILED)
        assert ably.connection.state == ConnectionState.FAILED
        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000
        await ably.close()

    async def test_connection_ping_closed(self):
        ably = await TestApp.get_ably_realtime()
        ably.connect()
        await ably.connection.once_async(ConnectionState.CONNECTED)
        await ably.close()
        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000

    async def test_auto_connect(self):
        ably = await TestApp.get_ably_realtime()
        connect_future = asyncio.Future()
        ably.connection.on(ConnectionState.CONNECTED, lambda change: connect_future.set_result(change))
        await connect_future
        assert ably.connection.state == ConnectionState.CONNECTED
        await ably.close()

    async def test_connection_state_change(self):
        ably = await TestApp.get_ably_realtime()

        connected_future = asyncio.Future()

        def on_state_change(change):
            connected_future.set_result(change)

        ably.connection.on(ConnectionState.CONNECTED, on_state_change)

        state_change = await connected_future
        assert state_change.previous == ConnectionState.CONNECTING
        assert state_change.current == ConnectionState.CONNECTED
        await ably.close()

    async def test_connection_state_change_reason(self):
        ably = await TestApp.get_ably_realtime(key=self.valid_key_format)

        state_change = await ably.connection.once_async()

        assert state_change.previous == ConnectionState.CONNECTING
        assert state_change.current == ConnectionState.FAILED
        assert ably.connection.error_reason is not None
        assert ably.connection.error_reason is state_change.reason
        await ably.close()

    async def test_realtime_request_timeout_connect(self):
        ably = await TestApp.get_ably_realtime(realtime_request_timeout=0.000001)
        state_change = await ably.connection.once_async()
        assert state_change.reason is not None
        assert state_change.reason.code == 50003
        assert state_change.reason.status_code == 504
        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert ably.connection.error_reason == state_change.reason
        await ably.close()

    async def test_realtime_request_timeout_ping(self):
        ably = await TestApp.get_ably_realtime(realtime_request_timeout=2000)
        await ably.connection.once_async(ConnectionState.CONNECTED)

        original_send_protocol_message = ably.connection.connection_manager.send_protocol_message

        async def new_send_protocol_message(protocol_message):
            if protocol_message.get('action') == ProtocolMessageAction.HEARTBEAT:
                return
            await original_send_protocol_message(protocol_message)

        ably.connection.connection_manager.send_protocol_message = new_send_protocol_message

        with pytest.raises(AblyException) as exception:
            await ably.connection.ping()

        assert exception.value.code == 50003
        assert exception.value.status_code == 504
        await ably.close()

    async def test_disconnected_retry_timeout(self):
        ably = await TestApp.get_ably_realtime(disconnected_retry_timeout=2000, auto_connect=False)
        original_connect = ably.connection.connection_manager.connect_base
        call_count = 0

        # intercept the library connection mechanism to fail the first two connection attempts
        async def new_connect():
            nonlocal call_count
            if call_count < 2:
                ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)
                call_count += 1
            else:
                await original_connect()

        ably.connection.connection_manager.connect_base = new_connect

        ably.connect()

        await ably.connection.once_async(ConnectionState.DISCONNECTED)

        # Test that the library eventually connects after two failed attempts
        await ably.connection.once_async(ConnectionState.CONNECTED)

        await ably.close()

    async def test_connectivity_check_default(self):
        ably = await TestApp.get_ably_realtime(auto_connect=False)
        # The default connectivity check should return True
        assert ably.connection.connection_manager.check_connection() is True

    async def test_connectivity_check_non_default(self):
        ably = await TestApp.get_ably_realtime(
            connectivity_check_url="https://echo.ably.io/respondWith?status=200", auto_connect=False)
        # A non-default URL should return True with a HTTP OK despite not returning "Yes" in the body
        assert ably.connection.connection_manager.check_connection() is True

    async def test_connectivity_check_bad_status(self):
        ably = await TestApp.get_ably_realtime(
            connectivity_check_url="https://echo.ably.io/respondWith?status=400", auto_connect=False)
        # Should return False when the URL returns a non-2xx response code
        assert ably.connection.connection_manager.check_connection() is False

    async def test_unroutable_host(self):
        ably = await TestApp.get_ably_realtime(realtime_host="10.255.255.1", realtime_request_timeout=3000)
        state_change = await ably.connection.once_async()
        assert state_change.reason
        assert state_change.reason.code == 50003
        assert state_change.reason.status_code == 504
        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert ably.connection.error_reason == state_change.reason
        await ably.close()

    async def test_invalid_host(self):
        ably = await TestApp.get_ably_realtime(realtime_host="iamnotahost")
        state_change = await ably.connection.once_async()
        assert state_change.reason
        assert state_change.reason.code == 40000
        assert state_change.reason.status_code == 400
        assert ably.connection.state == ConnectionState.DISCONNECTED
        assert ably.connection.error_reason == state_change.reason
        await ably.close()

    async def test_connection_state_ttl(self):
        Defaults.connection_state_ttl = 10
        ably = await TestApp.get_ably_realtime()

        state_change = await ably.connection.once_async()

        assert state_change.previous == ConnectionState.CONNECTING
        assert state_change.current == ConnectionState.SUSPENDED
        assert state_change.reason
        assert state_change.reason.code == 80002
        assert state_change.reason.status_code == 400
        assert ably.connection.connection_details is None
        await ably.close()

        Defaults.connection_state_ttl = 120000

    async def test_handle_connected(self):
        ably = await TestApp.get_ably_realtime()
        test_future = asyncio.Future()

        def on_update(connection_state):
            if connection_state.event == ConnectionEvent.UPDATE:
                test_future.set_result(connection_state)

        ably.connection.on(ConnectionEvent.UPDATE, on_update)

        async def on_transport_pending(transport):
            await transport.on_protocol_message({'action': 4, "connectionDetails": {"connectionStateTtl": 200}})

        ably.connection.connection_manager.on('transport.pending', on_transport_pending)

        state_change = await test_future

        assert state_change.previous == ConnectionState.CONNECTED
        assert state_change.current == ConnectionState.CONNECTED
        assert state_change.event == ConnectionEvent.UPDATE
        await ably.close()

    async def test_max_idle_interval(self):
        ably = await TestApp.get_ably_realtime(realtime_request_timeout=2000)

        def on_transport_pending(transport):
            original_on_protocol_message = transport.on_protocol_message

            async def on_protocol_message(msg):
                if msg["action"] == ProtocolMessageAction.CONNECTED:
                    msg["connectionDetails"]["maxIdleInterval"] = 100

                await original_on_protocol_message(msg)

            transport.on_protocol_message = on_protocol_message

        ably.connection.connection_manager.on('transport.pending', on_transport_pending)

        state_change = await ably.connection.once_async(ConnectionState.DISCONNECTED)

        assert state_change.previous == ConnectionState.CONNECTED
        assert state_change.current == ConnectionState.DISCONNECTED
        assert state_change.reason.code == 80003
        assert state_change.reason.status_code == 408

        await ably.close()

    # RTN15a
    async def test_retry_immediately_upon_unexpected_disconnection(self):
        # Set timeouts to 500s so that if the client uses retry delay the test will fail with a timeout
        ably = await TestApp.get_ably_realtime(
            disconnected_retry_timeout=500_000,
            suspended_retry_timeout=500_000
        )

        # Wait for the client to connect
        await ably.connection.once_async(ConnectionState.CONNECTED)

        # Simulate random loss of connection
        assert ably.connection.connection_manager.transport
        await ably.connection.connection_manager.transport.dispose()
        ably.connection.connection_manager.notify_state(ConnectionState.DISCONNECTED)
        assert ably.connection.state == ConnectionState.DISCONNECTED

        # Wait for the client to connect again
        await ably.connection.once_async(ConnectionState.CONNECTED)
        await ably.close()

    async def test_fallback_host(self):
        ably = await TestApp.get_ably_realtime()

        await ably.connection.connection_manager.once_async('transport.pending')
        assert ably.connection.connection_manager.transport
        ably.connection.connection_manager.transport._emit('failed', AblyException("test exception", 502, 50200))

        await ably.connection.once_async(ConnectionState.CONNECTED)

        assert ably.connection.connection_manager.transport.host != self.test_vars["realtime_host"]
        assert ably.options.fallback_realtime_host != self.test_vars["realtime_host"]
        await ably.close()

    async def test_fallback_host_no_connection(self):
        ably = await TestApp.get_ably_realtime()

        await ably.connection.connection_manager.once_async('transport.pending')
        assert ably.connection.connection_manager.transport

        def check_connection():
            return False

        ably.connection.connection_manager.check_connection = check_connection

        asyncio.create_task(ably.connection.connection_manager.transport.on_protocol_message({
            "action": ProtocolMessageAction.DISCONNECTED,
            "error": {
                "statusCode": 502,
                "code": 50200,
                "message": "test exception"
            }
        }))

        await ably.connection.once_async(ConnectionState.DISCONNECTED)

        assert ably.options.fallback_realtime_host is None
        await ably.close()

    async def test_fallback_host_disconnected_protocol_msg(self):
        ably = await TestApp.get_ably_realtime()

        await ably.connection.connection_manager.once_async('transport.pending')
        assert ably.connection.connection_manager.transport
        asyncio.create_task(ably.connection.connection_manager.transport.on_protocol_message({
            "action": ProtocolMessageAction.DISCONNECTED,
            "error": {
                "statusCode": 502,
                "code": 50200,
                "message": "test exception"
            }
        }))

        await ably.connection.once_async(ConnectionState.CONNECTED)

        assert ably.connection.connection_manager.transport.host != self.test_vars["realtime_host"]
        assert ably.options.fallback_realtime_host != self.test_vars["realtime_host"]
        await ably.close()

    #  RTN2d
    async def test_connection_null_client_id_query_params(self):
        rest = await TestApp.get_ably_rest()

        token_details = await rest.auth.request_token()

        realtime = await TestApp.get_ably_realtime(token_details=token_details)

        await realtime.connection.once_async(ConnectionState.CONNECTED)
        assert realtime.connection.connection_manager.transport.params.get("client_id") is None
        assert realtime.auth.client_id is None

        await realtime.close()
        await rest.close()

    async def test_connection_client_id_query_params(self):
        client_id = 'test_client_id'

        ably = await TestApp.get_ably_realtime(client_id=client_id)

        await ably.connection.once_async(ConnectionState.CONNECTED)
        assert ably.connection.connection_manager.transport.params["client_id"] == client_id
        assert ably.auth.client_id == client_id

        await ably.close()

    async def test_lost_connection_lifecycle(self):
        ably = await TestApp.get_ably_realtime(realtime_request_timeout=2000, disconnected_retry_timeout=2000)

        # when client connectivity is lost, the transport will become aware of a connectivity issue
        # when it stops seeing activity from realtime within maxIdleInterval, therefore setting the max idle
        # interval arbitrarily low will simulate client behaviour when connectivity is lost.
        def on_transport_pending(transport):
            original_on_protocol_message = transport.on_protocol_message

            async def on_protocol_message(msg):
                if msg["action"] == ProtocolMessageAction.CONNECTED:
                    msg["connectionDetails"]["maxIdleInterval"] = 1000

                await original_on_protocol_message(msg)

            transport.on_protocol_message = on_protocol_message

        ably.connection.connection_manager.once('transport.pending', on_transport_pending)

        # should transition to disconnected due to lack of activity from realtime
        await ably.connection.once_async(ConnectionState.DISCONNECTED)

        # should re-establish connection after disconnected_retry_timeout
        await ably.connection.once_async(ConnectionState.CONNECTED)

        await ably.close()
