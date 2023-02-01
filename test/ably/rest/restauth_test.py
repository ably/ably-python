import logging
import sys
import time
import uuid
import base64

import warnings
from urllib.parse import parse_qs
import mock
import pytest
import respx
from httpx import Response, AsyncClient

import ably
from ably import AblyRest
from ably import Auth
from ably import AblyAuthException
from ably.types.tokendetails import TokenDetails

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseAsyncTestCase

if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    from mock import AsyncMock

log = logging.getLogger(__name__)


# does not make any request, no need to vary by protocol
class TestAuth(BaseAsyncTestCase):
    async def asyncSetUp(self):
        self.test_vars = await RestSetup.get_test_vars()

    def test_auth_init_key_only(self):
        ably = AblyRest(key=self.test_vars["keys"][0]["key_str"])
        assert Auth.Method.BASIC == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.auth_options.key_name == self.test_vars["keys"][0]['key_name']
        assert ably.auth.auth_options.key_secret == self.test_vars["keys"][0]['key_secret']

    def test_auth_init_token_only(self):
        ably = AblyRest(token="this_is_not_really_a_token")

        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    def test_auth_token_details(self):
        td = TokenDetails()
        ably = AblyRest(token_details=td)

        assert Auth.Method.TOKEN == ably.auth.auth_mechanism
        assert ably.auth.token_details is td

    async def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(token_params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        ably = await RestSetup.get_ably_rest(
            key=None,
            key_name=self.test_vars["keys"][0]["key_name"],
            auth_callback=token_callback)

        try:
            await ably.stats(None)
        except Exception:
            pass

        assert callback_called, "Token callback not called"
        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    def test_auth_init_with_key_and_client_id(self):
        ably = AblyRest(key=self.test_vars["keys"][0]["key_str"], client_id='testClientId')

        assert Auth.Method.BASIC == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.client_id == 'testClientId'

    async def test_auth_init_with_token(self):
        ably = await RestSetup.get_ably_rest(key=None, token="this_is_not_really_a_token")
        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    # RSA11
    async def test_request_basic_auth_header(self):
        ably = AblyRest(key_secret='foo', key_name='bar')

        with mock.patch.object(AsyncClient, 'send') as get_mock:
            try:
                await ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        assert authorization == 'Basic %s' % base64.b64encode('bar:foo'.encode('ascii')).decode('utf-8')

    # RSA7e2
    async def test_request_basic_auth_header_with_client_id(self):
        ably = AblyRest(key_secret='foo', key_name='bar', client_id='client_id')

        with mock.patch.object(AsyncClient, 'send') as get_mock:
            try:
                await ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        client_id = request.headers['x-ably-clientid']
        assert client_id == base64.b64encode('client_id'.encode('ascii')).decode('utf-8')

    async def test_request_token_auth_header(self):
        ably = AblyRest(token='not_a_real_token')

        with mock.patch.object(AsyncClient, 'send') as get_mock:
            try:
                await ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        assert authorization == 'Bearer %s' % base64.b64encode('not_a_real_token'.encode('ascii')).decode('utf-8')

    def test_if_cant_authenticate_via_token(self):
        with pytest.raises(ValueError):
            AblyRest(use_token_auth=True)

    def test_use_auth_token(self):
        ably = AblyRest(use_token_auth=True, key=self.test_vars["keys"][0]["key_str"])
        assert ably.auth.auth_mechanism == Auth.Method.TOKEN

    def test_with_client_id(self):
        ably = AblyRest(use_token_auth=True, client_id='client_id', key=self.test_vars["keys"][0]["key_str"])
        assert ably.auth.auth_mechanism == Auth.Method.TOKEN

    def test_with_auth_url(self):
        ably = AblyRest(auth_url='auth_url')
        assert ably.auth.auth_mechanism == Auth.Method.TOKEN

    def test_with_auth_callback(self):
        ably = AblyRest(auth_callback=lambda x: x)
        assert ably.auth.auth_mechanism == Auth.Method.TOKEN

    def test_with_token(self):
        ably = AblyRest(token='a token')
        assert ably.auth.auth_mechanism == Auth.Method.TOKEN

    def test_default_ttl_is_1hour(self):
        one_hour_in_ms = 60 * 60 * 1000
        assert TokenDetails.DEFAULTS['ttl'] == one_hour_in_ms

    def test_with_auth_method(self):
        ably = AblyRest(token='a token', auth_method='POST')
        assert ably.auth.auth_options.auth_method == 'POST'

    def test_with_auth_headers(self):
        ably = AblyRest(token='a token', auth_headers={'h1': 'v1'})
        assert ably.auth.auth_options.auth_headers == {'h1': 'v1'}

    def test_with_auth_params(self):
        ably = AblyRest(token='a token', auth_params={'p': 'v'})
        assert ably.auth.auth_options.auth_params == {'p': 'v'}

    def test_with_default_token_params(self):
        ably = AblyRest(key=self.test_vars["keys"][0]["key_str"],
                        default_token_params={'ttl': 12345})
        assert ably.auth.auth_options.default_token_params == {'ttl': 12345}


class TestAuthAuthorize(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    async def asyncSetUp(self):
        self.ably = await RestSetup.get_ably_rest()
        self.test_vars = await RestSetup.get_test_vars()

    async def asyncTearDown(self):
        await self.ably.close()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    async def test_if_authorize_changes_auth_mechanism_to_token(self):
        assert Auth.Method.BASIC == self.ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

        await self.ably.auth.authorize()

        assert Auth.Method.TOKEN == self.ably.auth.auth_mechanism, "Authorise should change the Auth method"

    # RSA10a
    @dont_vary_protocol
    async def test_authorize_always_creates_new_token(self):
        await self.ably.auth.authorize({'capability': {'test': ['publish']}})
        await self.ably.channels.test.publish('event', 'data')

        await self.ably.auth.authorize({'capability': {'test': ['subscribe']}})
        with pytest.raises(AblyAuthException):
            await self.ably.channels.test.publish('event', 'data')

    async def test_authorize_create_new_token_if_expired(self):
        token = await self.ably.auth.authorize()
        with mock.patch('ably.rest.auth.Auth.token_details_has_expired',
                        return_value=True):
            new_token = await self.ably.auth.authorize()

        assert token is not new_token

    async def test_authorize_returns_a_token_details(self):
        token = await self.ably.auth.authorize()
        assert isinstance(token, TokenDetails)

    @dont_vary_protocol
    async def test_authorize_adheres_to_request_token(self):
        token_params = {'ttl': 10, 'client_id': 'client_id'}
        auth_params = {'auth_url': 'somewhere.com', 'query_time': True}
        with mock.patch('ably.rest.auth.Auth.request_token', new_callable=AsyncMock) as request_mock:
            await self.ably.auth.authorize(token_params, auth_params)

        token_called, auth_called = request_mock.call_args
        assert token_called[0] == token_params

        # Authorise may call request_token with some default auth_options.
        for arg, value in auth_params.items():
            assert auth_called[arg] == value, "%s called with wrong value: %s" % (arg, value)

    async def test_with_token_str_https(self):
        token = await self.ably.auth.authorize()
        token = token.token
        ably = await RestSetup.get_ably_rest(key=None, token=token, tls=True,
                                             use_binary_protocol=self.use_binary_protocol)
        await ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')
        await ably.close()

    async def test_with_token_str_http(self):
        token = await self.ably.auth.authorize()
        token = token.token
        ably = await RestSetup.get_ably_rest(key=None, token=token, tls=False,
                                             use_binary_protocol=self.use_binary_protocol)
        await ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')
        await ably.close()

    async def test_if_default_client_id_is_used(self):
        ably = await RestSetup.get_ably_rest(client_id='my_client_id',
                                             use_binary_protocol=self.use_binary_protocol)
        token = await ably.auth.authorize()
        assert token.client_id == 'my_client_id'
        await ably.close()

    # RSA10j
    async def test_if_parameters_are_stored_and_used_as_defaults(self):
        # Define some parameters
        auth_options = dict(self.ably.auth.auth_options.auth_options)
        auth_options['auth_headers'] = {'a_headers': 'a_value'}
        await self.ably.auth.authorize({'ttl': 555}, auth_options)
        with mock.patch('ably.rest.auth.Auth.request_token',
                        wraps=self.ably.auth.request_token) as request_mock:
            await self.ably.auth.authorize()

        token_called, auth_called = request_mock.call_args
        assert token_called[0] == {'ttl': 555}
        assert auth_called['auth_headers'] == {'a_headers': 'a_value'}

        # Different parameters, should completely replace the first ones, not merge
        auth_options = dict(self.ably.auth.auth_options.auth_options)
        auth_options['auth_headers'] = None
        await self.ably.auth.authorize({}, auth_options)
        with mock.patch('ably.rest.auth.Auth.request_token',
                        wraps=self.ably.auth.request_token) as request_mock:
            await self.ably.auth.authorize()

        token_called, auth_called = request_mock.call_args
        assert token_called[0] == {}
        assert auth_called['auth_headers'] is None

    # RSA10g
    async def test_timestamp_is_not_stored(self):
        # authorize once with arbitrary defaults
        auth_options = dict(self.ably.auth.auth_options.auth_options)
        auth_options['auth_headers'] = {'a_headers': 'a_value'}
        token_1 = await self.ably.auth.authorize(
            {'ttl': 60 * 1000, 'client_id': 'new_id'},
            auth_options)
        assert isinstance(token_1, TokenDetails)

        # call authorize again with timestamp set
        timestamp = await self.ably.time()
        with mock.patch('ably.rest.auth.TokenRequest',
                        wraps=ably.types.tokenrequest.TokenRequest) as tr_mock:
            auth_options = dict(self.ably.auth.auth_options.auth_options)
            auth_options['auth_headers'] = {'a_headers': 'a_value'}
            token_2 = await self.ably.auth.authorize(
                {'ttl': 60 * 1000, 'client_id': 'new_id', 'timestamp': timestamp},
                auth_options)
        assert isinstance(token_2, TokenDetails)
        assert token_1 != token_2
        assert tr_mock.call_args[1]['timestamp'] == timestamp

        # call authorize again with no params
        with mock.patch('ably.rest.auth.TokenRequest',
                        wraps=ably.types.tokenrequest.TokenRequest) as tr_mock:
            token_4 = await self.ably.auth.authorize()
        assert isinstance(token_4, TokenDetails)
        assert token_2 != token_4
        assert tr_mock.call_args[1]['timestamp'] != timestamp

    async def test_client_id_precedence(self):
        client_id = uuid.uuid4().hex
        overridden_client_id = uuid.uuid4().hex
        ably = await RestSetup.get_ably_rest(
            use_binary_protocol=self.use_binary_protocol,
            client_id=client_id,
            default_token_params={'client_id': overridden_client_id})
        token = await ably.auth.authorize()
        assert token.client_id == client_id
        assert ably.auth.client_id == client_id

        channel = ably.channels[
            self.get_channel_name('test_client_id_precedence')]
        await channel.publish('test', 'data')
        history = await channel.history()
        assert history.items[0].client_id == client_id
        await ably.close()

    # RSA10l
    @dont_vary_protocol
    async def test_authorise(self):
        with warnings.catch_warnings(record=True) as ws:
            # Cause all warnings to always be triggered
            warnings.simplefilter("always")

            token = await self.ably.auth.authorise()
            assert isinstance(token, TokenDetails)

            # Verify warning is raised
            ws = [w for w in ws if issubclass(w.category, DeprecationWarning)]
            assert len(ws) == 1


class TestRequestToken(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    async def asyncSetUp(self):
        self.test_vars = await RestSetup.get_test_vars()

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    async def test_with_key(self):
        ably = await RestSetup.get_ably_rest(use_binary_protocol=self.use_binary_protocol)

        token_details = await ably.auth.request_token()
        assert isinstance(token_details, TokenDetails)
        await ably.close()

        ably = await RestSetup.get_ably_rest(key=None, token_details=token_details,
                                             use_binary_protocol=self.use_binary_protocol)
        channel = self.get_channel_name('test_request_token_with_key')

        await ably.channels[channel].publish('event', 'foo')

        history = await ably.channels[channel].history()
        assert history.items[0].data == 'foo'
        await ably.close()

    @dont_vary_protocol
    @respx.mock
    async def test_with_auth_url_headers_and_params_POST(self):  # noqa: N802
        url = 'http://www.example.com'
        headers = {'foo': 'bar'}
        ably = await RestSetup.get_ably_rest(key=None, auth_url=url)

        auth_params = {'foo': 'auth', 'spam': 'eggs'}
        token_params = {'foo': 'token'}
        auth_route = respx.post(url)

        def call_back(request):
            assert request.headers['content-type'] == 'application/x-www-form-urlencoded'
            assert headers['foo'] == request.headers['foo']

            # TokenParams has precedence
            assert parse_qs(request.content.decode('utf-8')) == {'foo': ['token'], 'spam': ['eggs']}
            return Response(
                status_code=200,
                content="token_string"
            )

        auth_route.side_effect = call_back
        token_details = await ably.auth.request_token(
            token_params=token_params, auth_url=url, auth_headers=headers,
            auth_method='POST', auth_params=auth_params)

        assert 1 == auth_route.called
        assert isinstance(token_details, TokenDetails)
        assert 'token_string' == token_details.token
        await ably.close()

    @dont_vary_protocol
    @respx.mock
    async def test_with_auth_url_headers_and_params_GET(self):  # noqa: N802
        url = 'http://www.example.com'
        headers = {'foo': 'bar'}
        ably = await RestSetup.get_ably_rest(
            key=None, auth_url=url,
            auth_headers={'this': 'will_not_be_used'},
            auth_params={'this': 'will_not_be_used'})

        auth_params = {'foo': 'auth', 'spam': 'eggs'}
        token_params = {'foo': 'token'}
        auth_route = respx.get(url, params={'foo': ['token'], 'spam': ['eggs']})

        def call_back(request):
            assert request.headers['foo'] == 'bar'
            assert 'this' not in request.headers
            assert not request.content

            return Response(
                status_code=200,
                json={'issued': 1, 'token': 'another_token_string'}
            )
        auth_route.side_effect = call_back
        token_details = await ably.auth.request_token(
            token_params=token_params, auth_url=url, auth_headers=headers,
            auth_params=auth_params)
        assert 'another_token_string' == token_details.token
        await ably.close()

    @dont_vary_protocol
    async def test_with_callback(self):
        called_token_params = {'ttl': '3600000'}

        async def callback(token_params):
            assert token_params == called_token_params
            return 'token_string'

        ably = await RestSetup.get_ably_rest(key=None, auth_callback=callback)

        token_details = await ably.auth.request_token(
            token_params=called_token_params, auth_callback=callback)
        assert isinstance(token_details, TokenDetails)
        assert 'token_string' == token_details.token

        async def callback(token_params):
            assert token_params == called_token_params
            return TokenDetails(token='another_token_string')

        token_details = await ably.auth.request_token(
            token_params=called_token_params, auth_callback=callback)
        assert 'another_token_string' == token_details.token
        await ably.close()

    @dont_vary_protocol
    @respx.mock
    async def test_when_auth_url_has_query_string(self):
        url = 'http://www.example.com?with=query'
        headers = {'foo': 'bar'}
        ably = await RestSetup.get_ably_rest(key=None, auth_url=url)
        auth_route = respx.get('http://www.example.com', params={'with': 'query', 'spam': 'eggs'}).mock(
            return_value=Response(status_code=200, content='token_string'))
        await ably.auth.request_token(auth_url=url,
                                      auth_headers=headers,
                                      auth_params={'spam': 'eggs'})
        assert auth_route.called
        await ably.close()

    @dont_vary_protocol
    async def test_client_id_null_for_anonymous_auth(self):
        ably = await RestSetup.get_ably_rest(
            key=None,
            key_name=self.test_vars["keys"][0]["key_name"],
            key_secret=self.test_vars["keys"][0]["key_secret"])
        token = await ably.auth.authorize()

        assert isinstance(token, TokenDetails)
        assert token.client_id is None
        assert ably.auth.client_id is None
        await ably.close()

    @dont_vary_protocol
    async def test_client_id_null_until_auth(self):
        client_id = uuid.uuid4().hex
        token_ably = await RestSetup.get_ably_rest(
            default_token_params={'client_id': client_id})
        # before auth, client_id is None
        assert token_ably.auth.client_id is None

        token = await token_ably.auth.authorize()
        assert isinstance(token, TokenDetails)

        # after auth, client_id is defined
        assert token.client_id == client_id
        assert token_ably.auth.client_id == client_id
        await token_ably.close()


class TestRenewToken(BaseAsyncTestCase):

    async def asyncSetUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.ably = await RestSetup.get_ably_rest(use_binary_protocol=False)
        # with headers
        self.publish_attempts = 0
        self.channel = uuid.uuid4().hex
        host = self.test_vars['host']
        tokens = ['a_token', 'another_token']
        headers = {'Content-Type': 'application/json'}
        self.mocked_api = respx.mock(base_url='https://{}'.format(host))
        self.request_token_route = self.mocked_api.post(
            "/keys/{}/requestToken".format(self.test_vars["keys"][0]['key_name']),
            name="request_token_route")
        self.request_token_route.return_value = Response(
            status_code=200,
            headers=headers,
            json={
                'token': tokens[self.request_token_route.call_count - 1],
                'expires': (time.time() + 60) * 1000
            },
        )

        def call_back(request):
            self.publish_attempts += 1
            if self.publish_attempts in [1, 3]:
                return Response(
                    status_code=201,
                    headers=headers,
                    json=[],
                )
            return Response(
                status_code=401,
                headers=headers,
                json={
                    'error': {'message': 'Authentication failure', 'statusCode': 401, 'code': 40140}
                },
            )

        self.publish_attempt_route = self.mocked_api.post("/channels/{}/messages".format(self.channel),
                                                          name="publish_attempt_route")
        self.publish_attempt_route.side_effect = call_back
        self.mocked_api.start()

    async def asyncTearDown(self):
        # We need to have quiet here in order to do not have check if all endpoints were called
        self.mocked_api.stop(quiet=True)
        self.mocked_api.reset()
        await self.ably.close()

    # RSA4b
    async def test_when_renewable(self):
        await self.ably.auth.authorize()
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.mocked_api["request_token_route"].call_count == 1
        assert self.publish_attempts == 1

        # Triggers an authentication 401 failure which should automatically request a new token
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.mocked_api["request_token_route"].call_count == 2
        assert self.publish_attempts == 3

    # RSA4a
    async def test_when_not_renewable(self):
        await self.ably.close()

        self.ably = await RestSetup.get_ably_rest(
            key=None,
            token='token ID cannot be used to create a new token',
            use_binary_protocol=False)
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 1

        publish = self.ably.channels[self.channel].publish

        match = "The provided token is not renewable and there is no means to generate a new token"
        with pytest.raises(AblyAuthException, match=match):
            await publish('evt', 'msg')

        assert not self.mocked_api["request_token_route"].called

    # RSA4a
    async def test_when_not_renewable_with_token_details(self):
        token_details = TokenDetails(token='a_dummy_token')
        self.ably = await RestSetup.get_ably_rest(
            key=None,
            token_details=token_details,
            use_binary_protocol=False)
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.mocked_api["publish_attempt_route"].call_count == 1

        publish = self.ably.channels[self.channel].publish

        match = "The provided token is not renewable and there is no means to generate a new token"
        with pytest.raises(AblyAuthException, match=match):
            await publish('evt', 'msg')

        assert not self.mocked_api["request_token_route"].called


class TestRenewExpiredToken(BaseAsyncTestCase):

    async def asyncSetUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.publish_attempts = 0
        self.channel = uuid.uuid4().hex

        host = self.test_vars['host']
        key = self.test_vars["keys"][0]['key_name']
        headers = {'Content-Type': 'application/json'}

        self.mocked_api = respx.mock(base_url='https://{}'.format(host))
        self.request_token_route = self.mocked_api.post("/keys/{}/requestToken".format(key),
                                                        name="request_token_route")
        self.request_token_route.return_value = Response(
            status_code=200,
            headers=headers,
            json={
                'token': 'a_token',
                'expires': int(time.time() * 1000),  # Always expires
            }
        )
        self.publish_message_route = self.mocked_api.post("/channels/{}/messages".format(self.channel),
                                                          name="publish_message_route")
        self.time_route = self.mocked_api.get("/time", name="time_route")
        self.time_route.return_value = Response(
            status_code=200,
            headers=headers,
            json=[int(time.time() * 1000)]
        )

        def cb_publish(request):
            self.publish_attempts += 1
            if self.publish_fail:
                self.publish_fail = False
                return Response(
                    status_code=401,
                    json={
                        'error': {'message': 'Authentication failure', 'statusCode': 401, 'code': 40140}
                    }
                )
            return Response(
                status_code=201,
                json='[]'
            )

        self.publish_message_route.side_effect = cb_publish
        self.mocked_api.start()

    async def asyncTearDown(self):
        self.mocked_api.stop(quiet=True)
        self.mocked_api.reset()

    # RSA4b1
    async def test_query_time_false(self):
        ably = await RestSetup.get_ably_rest()
        await ably.auth.authorize()
        self.publish_fail = True
        await ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 2
        await ably.close()

    # RSA4b1
    async def test_query_time_true(self):
        ably = await RestSetup.get_ably_rest(query_time=True)
        await ably.auth.authorize()
        self.publish_fail = False
        await ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 1
        await ably.close()
