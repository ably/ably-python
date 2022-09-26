import asyncio
from ably.realtime.connection import ConnectionState
import pytest
from ably.util.exceptions import AblyAuthException
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeAuth(BaseAsyncTestCase):
    async def setUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.valid_key_format = "api:key"

    async def test_auth_connection(self):
        ably = await RestSetup.get_ably_realtime()
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
