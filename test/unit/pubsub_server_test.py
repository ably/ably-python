import warnings

import pytest

import ably
from ably import AblyRealtime, AblyRest
from ably.pubsub import server
from ably.pubsub.server import create_http_client, create_realtime_client
from ably.pubsub.server import sync as server_sync
from ably.sync import AblyRestSync


class TestPubSubServer:

    def test_version_matches_the_core_it_pins(self):
        assert server.__version__ == ably.lib_version

    def test_clients_are_the_core_clients(self):
        assert isinstance(create_http_client(token='foo'), AblyRest)
        assert isinstance(create_realtime_client(token='foo', auto_connect=False), AblyRealtime)
        assert isinstance(server_sync.create_http_client(token='foo'), AblyRestSync)

    def test_options_are_passed_through(self):
        client = create_http_client(key='name:secret', client_id='me', tls=False)
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'
        assert client.options.tls is False

    def test_realtime_options_are_passed_through(self):
        client = create_realtime_client(key='name:secret', client_id='me', auto_connect=False)
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'

    def test_sync_options_are_passed_through(self):
        client = server_sync.create_http_client(key='name:secret', client_id='me')
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'

    def test_the_key_can_be_positional_as_on_the_constructor(self):
        assert create_http_client('name:secret').options.key_name == 'name'
        assert create_realtime_client('name:secret', auto_connect=False).options.key_name == 'name'
        assert server_sync.create_http_client('name:secret').options.key_name == 'name'

    def test_token_auth_is_passed_through(self):
        assert create_http_client(token='foo').options.auth_token == 'foo'

    def test_authentication_is_still_required(self):
        with pytest.raises(ValueError):
            create_http_client()

    # The factory is the recommended entry point, so it has nothing to warn about
    @pytest.mark.parametrize('factory,kwargs', [
        (create_http_client, {}),
        (create_realtime_client, {'auto_connect': False}),
        (server_sync.create_http_client, {}),
    ])
    def test_factories_do_not_warn(self, factory, kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            factory(token='foo', **kwargs)

    def test_the_constructors_still_warn_after_a_factory_call(self):
        create_http_client(token='foo')
        with pytest.warns(DeprecationWarning):
            AblyRest(token='foo')
