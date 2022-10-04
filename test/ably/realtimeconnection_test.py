import asyncio
from ably.realtime.connection import ConnectionState
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
        with pytest.raises(AblyAuthException):
            await ably.connect()
        assert ably.connection.state == ConnectionState.FAILED
        await ably.close()

    async def test_connection_ping_connected(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        response_time_ms = await ably.ping()
        assert response_time_ms is not None
        assert type(response_time_ms) is float
        await ably.close()

    async def test_connection_ping_initialized(self):
        ably = await RestSetup.get_ably_realtime(auto_connect=False)
        assert ably.connection.state == ConnectionState.INITIALIZED
        with pytest.raises(AblyException) as exception:
            await ably.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000

    async def test_connection_ping_failed(self):
        ably = await RestSetup.get_ably_realtime(key=self.valid_key_format)
        with pytest.raises(AblyAuthException):
            await ably.connect()
        assert ably.connection.state == ConnectionState.FAILED
        with pytest.raises(AblyException) as exception:
            await ably.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000
        await ably.close()

    async def test_connection_ping_closed(self):
        ably = await RestSetup.get_ably_realtime()
        await ably.connect()
        assert ably.connection.state == ConnectionState.CONNECTED
        await ably.close()
        with pytest.raises(AblyException) as exception:
            await ably.ping()
        assert exception.value.code == 400
        assert exception.value.status_code == 40000
