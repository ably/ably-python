from ably.realtime.connection import ConnectionState
from ably.types.tokendetails import TokenDetails
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeAuth(BaseAsyncTestCase):
    async def asyncSetUp(self):
        self.test_vars = await TestApp.get_test_vars()
        self.valid_key_format = "api:key"

    async def test_auth_valid_api_key(self):
        ably = await TestApp.get_ably_realtime()
        await ably.connection.once_async(ConnectionState.CONNECTED)
        assert ably.connection.error_reason is None
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        await ably.close()

    async def test_auth_wrong_api_key(self):
        api_key = "js9de7r:08sdnuvfasd"
        ably = await TestApp.get_ably_realtime(key=api_key)
        state_change = await ably.connection.once_async(ConnectionState.FAILED)
        assert ably.connection.error_reason == state_change.reason
        assert state_change.reason.code == 40005
        assert state_change.reason.status_code == 400
        await ably.close()

    async def test_auth_with_token_str(self):
        self.rest = await TestApp.get_ably_rest()
        token_details = await self.rest.auth.request_token()
        ably = await TestApp.get_ably_realtime(token=token_details.token)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_invalid_token_str(self):
        invalid_token = "Sdnurv_some_invalid_token_nkds9r7"
        ably = await TestApp.get_ably_realtime(token=invalid_token)
        state_change = await ably.connection.once_async(ConnectionState.FAILED)
        assert state_change.reason.code == 40005
        assert state_change.reason.status_code == 400
        await ably.close()

    async def test_auth_with_token_details(self):
        self.rest = await TestApp.get_ably_rest()
        token_details = await self.rest.auth.request_token()
        ably = await TestApp.get_ably_realtime(token_details=token_details)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_invalid_token_details(self):
        invalid_token_details = TokenDetails(token="invalid-token")
        ably = await TestApp.get_ably_realtime(token_details=invalid_token_details)
        state_change = await ably.connection.once_async(ConnectionState.FAILED)
        assert state_change.reason.code == 40005
        assert state_change.reason.status_code == 400
        await ably.close()
