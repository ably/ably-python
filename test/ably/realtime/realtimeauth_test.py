import json
from ably.realtime.connection import ConnectionState
from ably.types.tokendetails import TokenDetails
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeAuth(BaseAsyncTestCase):
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

    async def test_auth_with_token_string(self):
        rest = await TestApp.get_ably_rest()
        token_details = await rest.auth.request_token()
        ably = await TestApp.get_ably_realtime(token=token_details.token)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_invalid_token_string(self):
        invalid_token = "Sdnurv_some_invalid_token_nkds9r7"
        ably = await TestApp.get_ably_realtime(token=invalid_token)
        state_change = await ably.connection.once_async(ConnectionState.FAILED)
        assert state_change.reason.code == 40005
        assert state_change.reason.status_code == 400
        await ably.close()

    async def test_auth_with_token_details(self):
        rest = await TestApp.get_ably_rest()
        token_details = await rest.auth.request_token()
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

    async def test_auth_with_auth_callback_with_token_request(self):
        rest = await TestApp.get_ably_rest()

        async def callback(params):
            token_details = await rest.auth.create_token_request(token_params=params)
            return token_details

        ably = await TestApp.get_ably_realtime(auth_callback=callback)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_auth_callback_token_with_details(self):
        rest = await TestApp.get_ably_rest()

        async def callback(params):
            token_details = await rest.auth.request_token(token_params=params)
            return token_details

        ably = await TestApp.get_ably_realtime(auth_callback=callback)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_auth_callback_with_token_string(self):
        rest = await TestApp.get_ably_rest()

        async def callback(params):
            token_details = await rest.auth.request_token(token_params=params)
            return token_details.token

        ably = await TestApp.get_ably_realtime(auth_callback=callback)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_auth_callback_invalid_token(self):
        async def callback(params):
            return "invalid token"

        ably = await TestApp.get_ably_realtime(auth_callback=callback)
        state_change = await ably.connection.once_async(ConnectionState.FAILED)
        assert state_change.reason.code == 40005
        assert state_change.reason.status_code == 400
        await ably.close()

    async def test_auth_with_auth_url_json(self):
        echo_url = 'https://echo.ably.io'
        rest = await TestApp.get_ably_rest()
        token_details = await rest.auth.request_token()
        token_details_json = json.dumps(token_details.to_dict())
        url_path = f"{echo_url}/?type=json&body={token_details_json}"

        ably = await TestApp.get_ably_realtime(auth_url=url_path)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_auth_url_text_plain(self):
        echo_url = 'https://echo.ably.io'
        rest = await TestApp.get_ably_rest()
        token_details = await rest.auth.request_token()
        url_path = f"{echo_url}/?type=text&body={token_details.token}"

        ably = await TestApp.get_ably_realtime(auth_url=url_path)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()

    async def test_auth_with_auth_url_post(self):
        echo_url = 'https://echo.ably.io'
        rest = await TestApp.get_ably_rest()
        token_details = await rest.auth.request_token()
        url_path = f"{echo_url}/?type=json&"

        ably = await TestApp.get_ably_realtime(auth_url=url_path, auth_method='POST',
                                               auth_params=token_details)
        await ably.connection.once_async(ConnectionState.CONNECTED)
        response_time_ms = await ably.connection.ping()
        assert response_time_ms is not None
        assert ably.connection.error_reason is None
        await ably.close()
