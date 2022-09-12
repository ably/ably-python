import pytest
from ably import Auth, AblyRealtime
from ably.util.exceptions import AblyAuthException
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeAuth(BaseAsyncTestCase):
    async def setUp(self):
        self.invalid_key = "some key"
        self.valid_key_format = "Vjhddw.owt:R97sjjbdERJdjwer"

    def test_auth_with_correct_key_format(self):
        key = self.valid_key_format.split(":")
        ably = AblyRealtime(self.valid_key_format)
        assert Auth.Method.BASIC == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.auth_options.key_name == key[0]
        assert ably.auth.auth_options.key_secret == key[1]

    def test_auth_incorrect_key_format(self):
        with pytest.raises(AblyAuthException):
            ably = AblyRealtime(self.invalid_key)