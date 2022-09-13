import pytest
from ably import Auth, AblyRealtime
from ably.util.exceptions import AblyAuthException
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeAuth(BaseAsyncTestCase):
    async def setUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.valid_key_format = "Vjdw.owt:R97sjjjwer"

    async def test_auth_with_valid_key(self):
        ably = AblyRealtime(self.test_vars["keys"][0]["key_str"])
        assert Auth.Method.BASIC == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.auth_options.key_name == self.test_vars["keys"][0]['key_name']
        assert ably.auth.auth_options.key_secret == self.test_vars["keys"][0]['key_secret']

    async def test_auth_incorrect_key(self):
        with pytest.raises(AblyAuthException):
            AblyRealtime("some invalid key")

    async def test_auth_with_valid_key_format(self):
        key = self.valid_key_format.split(":")
        ably = AblyRealtime(self.valid_key_format)
        assert Auth.Method.BASIC == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.auth_options.key_name == key[0]
        assert ably.auth.auth_options.key_secret == key[1]

    # async def test_auth_connection(self):
    #     ably = AblyRealtime(self.test_vars["keys"][0]["key_str"])
    #     conn = await ably.connection.connect()
    #     assert conn["action"] == 4
    #     assert "connectionDetails" in conn

    async def test_auth_invalid_key(self):
        ably = AblyRealtime(self.valid_key_format)
        with pytest.raises(AblyAuthException):
            await ably.connection.connect()
        
