import warnings

import pytest

import ably
from ably import AblyRealtime
from ably.pubsub import device
from ably.pubsub.device import create_client


class TestPubSubDevice:

    def test_version_matches_the_core_it_pins(self):
        assert device.__version__ == ably.lib_version

    def test_client_is_the_core_realtime_client(self):
        assert isinstance(create_client(token='foo', auto_connect=False), AblyRealtime)

    def test_options_are_passed_through(self):
        client = create_client(key='name:secret', client_id='me', auto_connect=False)
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'
        assert client.options.auto_connect is False

    def test_the_key_can_be_positional_as_on_the_constructor(self):
        assert create_client('name:secret', auto_connect=False).options.key_name == 'name'

    def test_token_auth_is_passed_through(self):
        assert create_client(token='foo', auto_connect=False).options.auth_token == 'foo'

    def test_authentication_is_still_required(self):
        with pytest.raises(ValueError):
            create_client(auto_connect=False)

    # The factory is the recommended entry point, so it has nothing to warn about
    def test_the_factory_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            create_client(token='foo', auto_connect=False)

    def test_the_constructor_still_warns_after_a_factory_call(self):
        create_client(token='foo', auto_connect=False)
        with pytest.warns(DeprecationWarning):
            AblyRealtime(token='foo', auto_connect=False)
