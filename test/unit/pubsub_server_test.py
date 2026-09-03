"""The `ably_pubsub.server` factory doors.

The doors are the entry points of the server distribution: they construct the
core's clients unchanged, and they stamp the agent entry that declares the
server side. The header assertions here are what billing reads, so they are
written to fail loudly rather than to be forgiving.
"""

import re

import httpx
import pytest
import respx
from mock import MagicMock, patch
from websockets.exceptions import WebSocketException

import ably_pubsub.core
from ably_pubsub.core import AblyRealtime, AblyRest
from ably_pubsub.core.sync import AblyRestSync
from ably_pubsub.core.transport.websockettransport import WebSocketTransport
from ably_pubsub.core.util.exceptions import AblyException
from ably_pubsub.server import (
    SERVER_AGENT_IDENTIFIER,
    create_http_client,
    create_realtime_client,
)
from ably_pubsub.server import sync as server_sync

# The versionless side flag comes last, after the library and runtime entries.
# `ably-pubsub-server/<anything>` is the regression ably-js#2297 guards against:
# a `name/None` rendering would send a version the registry does not define.
SERVER_AGENT = re.compile(r'^ably-pubsub-python/\d+\.\d+\.\d+(\S*)? python/\S+ ably-pubsub-server$')

TEST_KEY = 'name:secret'


def assert_declares_the_server_side(agent):
    assert SERVER_AGENT.match(agent), agent
    assert f'{SERVER_AGENT_IDENTIFIER}/' not in agent, agent


async def agent_header_of(client):
    """The Ably-Agent an HTTP client puts on the wire."""
    with respx.mock:
        route = respx.get(url__regex=r'.*/time').mock(
            return_value=httpx.Response(200, json=[1234567890000]))
        await client.time()
    return route.calls.last.request.headers['Ably-Agent']


def sync_agent_header_of(client):
    with respx.mock:
        route = respx.get(url__regex=r'.*/time').mock(
            return_value=httpx.Response(200, json=[1234567890000]))
        client.time()
    return route.calls.last.request.headers['Ably-Agent']


class TestFactories:
    """The doors return the core's clients, and pass everything through."""

    def test_clients_are_the_core_clients(self):
        assert isinstance(create_http_client(token='foo'), AblyRest)
        assert isinstance(create_realtime_client(token='foo', auto_connect=False), AblyRealtime)
        assert isinstance(server_sync.create_http_client(token='foo'), AblyRestSync)

    def test_the_version_is_the_core_version(self):
        assert ably_pubsub.server.__version__ == ably_pubsub.core.lib_version

    def test_options_are_passed_through(self):
        client = create_http_client(key=TEST_KEY, client_id='me', tls=False)
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'
        assert client.options.tls is False

    def test_realtime_options_are_passed_through(self):
        client = create_realtime_client(key=TEST_KEY, client_id='me', auto_connect=False)
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'

    def test_sync_options_are_passed_through(self):
        client = server_sync.create_http_client(key=TEST_KEY, client_id='me', tls=False)
        assert client.options.key_name == 'name'
        assert client.options.client_id == 'me'
        assert client.options.tls is False

    def test_the_key_can_be_positional_as_on_the_constructor(self):
        assert create_http_client(TEST_KEY).options.key_name == 'name'
        assert create_realtime_client(TEST_KEY, auto_connect=False).options.key_name == 'name'
        assert server_sync.create_http_client(TEST_KEY).options.key_name == 'name'

    def test_token_auth_is_passed_through(self):
        assert create_http_client(token='foo').options.auth_token == 'foo'

    def test_authentication_is_still_required(self):
        with pytest.raises(ValueError):
            create_http_client()

    def test_everything_declared_public_is_importable(self):
        for module in (ably_pubsub.server, server_sync):
            missing = [name for name in module.__all__ if not hasattr(module, name)]
            assert missing == []


class TestAgentHeader:

    async def test_the_http_door_declares_the_server_side(self):
        client = create_http_client(TEST_KEY)
        assert_declares_the_server_side(await agent_header_of(client))
        await client.close()

    def test_the_sync_http_door_declares_the_server_side(self):
        client = server_sync.create_http_client(TEST_KEY)
        assert_declares_the_server_side(sync_agent_header_of(client))
        client.close()

    async def test_the_realtime_door_declares_the_server_side_on_the_handshake(self):
        client = create_realtime_client(TEST_KEY, auto_connect=False)
        connect = MagicMock(side_effect=WebSocketException('not connecting in a unit test'))
        with patch('ably_pubsub.core.transport.websockettransport.ws_connect', connect):
            transport = WebSocketTransport(client.connection.connection_manager, 'realtime.example', {})
            transport.connect()
            # The connection cannot succeed here; what matters is the headers it
            # handed to websockets before failing.
            with pytest.raises(AblyException):
                await transport.ws_connect_task
        headers = connect.call_args.kwargs['additional_headers']
        assert_declares_the_server_side(headers['Ably-Agent'])
        await client.close()

    async def test_the_core_client_alone_declares_no_side(self):
        client = AblyRest(TEST_KEY)
        agent = await agent_header_of(client)
        assert re.match(r'^ably-pubsub-python/\d+\.\d+\.\d+(\S*)? python/\S+$', agent), agent
        assert SERVER_AGENT_IDENTIFIER not in agent
        await client.close()

    async def test_caller_supplied_agents_survive(self):
        client = create_http_client(TEST_KEY, agents={'my-sdk': '1.0'})
        agent = await agent_header_of(client)
        assert 'my-sdk/1.0' in agent
        assert agent.endswith(f' {SERVER_AGENT_IDENTIFIER}')
        await client.close()

    async def test_the_side_entry_cannot_be_overridden_by_the_caller(self):
        client = create_http_client(TEST_KEY, agents={SERVER_AGENT_IDENTIFIER: 'x'})
        assert_declares_the_server_side(await agent_header_of(client))
        await client.close()

    def test_a_versionless_agent_renders_as_a_bare_flag(self):
        from ably_pubsub.core.http.httputils import HttpUtils
        agent = HttpUtils.default_headers(agents={'flag': None, 'versioned': '1.2'})['Ably-Agent']
        assert agent.endswith('flag versioned/1.2')
