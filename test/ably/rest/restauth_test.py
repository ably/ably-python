import json
import logging
import sys
import time
import uuid
import base64

from urllib.parse import parse_qs
import mock
import pytest
import responses
from niquests import AsyncSession

import ably
from ably import AblyRest
from ably import Auth
from ably import AblyAuthException
from ably.types.tokendetails import TokenDetails

from test.ably.testapp import TestApp
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseAsyncTestCase

if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    from mock import AsyncMock

log = logging.getLogger(__name__)


# does not make any request, no need to vary by protocol
class TestAuth(BaseAsyncTestCase):
    async def asyncSetUp(self):
        self.test_vars = await TestApp.get_test_vars()

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

        ably = await TestApp.get_ably_rest(
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
        ably = await TestApp.get_ably_rest(key=None, token="this_is_not_really_a_token")
        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    # RSA11
    async def test_request_basic_auth_header(self):
        ably = AblyRest(key_secret='foo', key_name='bar')

        with mock.patch.object(AsyncSession, 'send') as get_mock:
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

        with mock.patch.object(AsyncSession, 'send') as get_mock:
            try:
                await ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        client_id = request.headers['x-ably-clientid']
        assert client_id == base64.b64encode('client_id'.encode('ascii'))

    async def test_request_token_auth_header(self):
        ably = AblyRest(token='not_a_real_token')

        with mock.patch.object(AsyncSession, 'send') as get_mock:
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
        self.ably = await TestApp.get_ably_rest()
        self.test_vars = await TestApp.get_test_vars()

    async def asyncTearDown(self):
        await self.ably.close()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    async def test_if_authorize_changes_auth_mechanism_to_token(self):
        assert Auth.Method.BASIC == self.ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

        await self.ably.auth.authorize()

        assert Auth.Method.TOKEN == self.ably.auth.auth_mechanism, "Authorize should change the Auth method"

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

        # Authorize may call request_token with some default auth_options.
        for arg, value in auth_params.items():
            assert auth_called[arg] == value, "%s called with wrong value: %s" % (arg, value)

    async def test_with_token_str_https(self):
        token = await self.ably.auth.authorize()
        token = token.token
        ably = await TestApp.get_ably_rest(key=None, token=token, tls=True,
                                           use_binary_protocol=self.use_binary_protocol)
        await ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')
        await ably.close()

    async def test_with_token_str_http(self):
        token = await self.ably.auth.authorize()
        token = token.token
        ably = await TestApp.get_ably_rest(key=None, token=token, tls=False,
                                           use_binary_protocol=self.use_binary_protocol)
        await ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')
        await ably.close()

    async def test_if_default_client_id_is_used(self):
        ably = await TestApp.get_ably_rest(client_id='my_client_id',
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
        ably = await TestApp.get_ably_rest(
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


class TestRequestToken(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    async def asyncSetUp(self):
        self.test_vars = await TestApp.get_test_vars()

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    async def test_with_key(self):
        ably = await TestApp.get_ably_rest(use_binary_protocol=self.use_binary_protocol)

        token_details = await ably.auth.request_token()
        assert isinstance(token_details, TokenDetails)
        await ably.close()

        ably = await TestApp.get_ably_rest(key=None, token_details=token_details,
                                           use_binary_protocol=self.use_binary_protocol)
        channel = self.get_channel_name('test_request_token_with_key')

        await ably.channels[channel].publish('event', 'foo')

        history = await ably.channels[channel].history()
        assert history.items[0].data == 'foo'
        await ably.close()

    @dont_vary_protocol
    @responses.activate
    async def test_with_auth_url_headers_and_params_http_post(self):  # noqa: N802
        url = 'http://www.example.com/'
        headers = {'foo': 'bar'}
        ably = await TestApp.get_ably_rest(key=None, auth_url=url)

        auth_params = {'foo': 'auth', 'spam': 'eggs'}
        token_params = {'foo': 'token'}

        count_call = 0

        def call_back(request):
            nonlocal count_call
            assert request.headers['content-type'] == 'application/x-www-form-urlencoded'
            assert headers['foo'] == request.headers['foo']

            # TokenParams has precedence
            assert parse_qs(request.body) == {'foo': ['token'], 'spam': ['eggs']}

            count_call += 1

            return (
                200,
                {
                    "Content-Type": "text/plain",
                },
                "token_string",
            )

        responses.add_callback(
            "POST",
            url,
            call_back
        )

        token_details = await ably.auth.request_token(
            token_params=token_params, auth_url=url, auth_headers=headers,
            auth_method='POST', auth_params=auth_params)

        assert isinstance(token_details, TokenDetails)
        assert 1 == count_call
        assert 'token_string' == token_details.token
        await ably.close()

    @dont_vary_protocol
    @responses.activate
    async def test_with_auth_url_headers_and_params_http_get(self):  # noqa: N802
        url = 'http://www.example.com/'
        headers = {'foo': 'bar'}
        ably = await TestApp.get_ably_rest(
            key=None, auth_url=url,
            auth_headers={'this': 'will_not_be_used'},
            auth_params={'this': 'will_not_be_used'})

        auth_params = {'foo': 'auth', 'spam': 'eggs'}
        token_params = {'foo': 'token'}

        call_count = 0

        def call_back(request):
            nonlocal call_count

            assert request.headers['foo'] == 'bar'
            assert 'this' not in request.headers
            assert not request.body

            call_count += 1

            return (
                200,
                {
                    "content-type": "application/json"
                },
                json.dumps(
                    {'issued': 1, 'token': 'another_token_string'}
                )
            )

        responses.add_callback(
            "GET",
            f"{url}?foo=token&spam=eggs",
            call_back,
            content_type="application/json",
        )

        token_details = await ably.auth.request_token(
            token_params=token_params, auth_url=url, auth_headers=headers,
            auth_params=auth_params)
        assert 'another_token_string' == token_details.token
        assert call_count
        await ably.close()

    @dont_vary_protocol
    async def test_with_callback(self):
        called_token_params = {'ttl': '3600000'}

        async def callback(token_params):
            assert token_params == called_token_params
            return 'token_string'

        ably = await TestApp.get_ably_rest(key=None, auth_callback=callback)

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
    @responses.activate
    async def test_when_auth_url_has_query_string(self):
        url = 'http://www.example.com/?with=query'
        headers = {'foo': 'bar'}
        ably = await TestApp.get_ably_rest(key=None, auth_url=url)
        auth_route = responses.get(
            'http://www.example.com/?with=query&spam=eggs',
            status=200,
            body='token_string',
            headers={"Content-Type": "text/plain"}
        )

        await ably.auth.request_token(auth_url=url,
                                      auth_headers=headers,
                                      auth_params={'spam': 'eggs'})
        assert auth_route.call_count
        await ably.close()

    @dont_vary_protocol
    async def test_client_id_null_for_anonymous_auth(self):
        ably = await TestApp.get_ably_rest(
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
        token_ably = await TestApp.get_ably_rest(
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
        self.test_vars = await TestApp.get_test_vars()
        self.host = 'fake-host.ably.io'
        self.ably = await TestApp.get_ably_rest(use_binary_protocol=False, rest_host=self.host)
        # with headers
        self.publish_attempts = 0
        self.channel = uuid.uuid4().hex

        key = self.test_vars['keys'][0]['key_name']
        tokens = ['a_token', 'another_token']

        self.base_url = 'https://{}'.format(self.host)

        self.request_token_route = responses.post(
            f"{self.base_url}/keys/{key}/requestToken",
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    'token': tokens[1],
                    'expires': (time.time() + 60) * 1000
                }
            )
        )

        def call_back(request):
            self.publish_attempts += 1
            if self.publish_attempts in [1, 3]:
                return (
                    201,
                    {},
                    "[]"
                )
            return (
                401,
                {},
                json.dumps(
                    {
                        'error': {'message': 'Authentication failure', 'statusCode': 401, 'code': 40140}
                    }
                )
            )

        responses.add_callback(
            "POST",
            f"{self.base_url}/channels/{self.channel}/messages",
            call_back,
            content_type="application/json",
        )

        responses.start()

    async def asyncTearDown(self):
        # We need to have quiet here in order to do not have check if all endpoints were called
        responses.stop()
        responses.reset()
        await self.ably.close()

    # RSA4b
    async def test_when_renewable(self):
        await self.ably.auth.authorize()
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.request_token_route.call_count == 1
        assert self.publish_attempts == 1

        # Triggers an authentication 401 failure which should automatically request a new token
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.request_token_route.call_count == 2
        assert self.publish_attempts == 3

    # RSA4a
    async def test_when_not_renewable(self):
        await self.ably.close()

        self.ably = await TestApp.get_ably_rest(
            key=None,
            rest_host=self.host,
            token='token ID cannot be used to create a new token',
            use_binary_protocol=False)
        await self.ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 1

        publish = self.ably.channels[self.channel].publish

        match = "Need a new token but auth_options does not include a way to request one"
        with pytest.raises(AblyAuthException, match=match):
            await publish('evt', 'msg')

        assert not self.request_token_route.call_count

    # RSA4a
    async def test_when_not_renewable_with_token_details(self):
        token_details = TokenDetails(token='a_dummy_token')
        self.ably = await TestApp.get_ably_rest(
            key=None,
            rest_host=self.host,
            token_details=token_details,
            use_binary_protocol=False)
        await self.ably.channels[self.channel].publish('evt', 'msg')

        responses.assert_call_count(f"{self.base_url}/channels/{self.channel}/messages", 1)

        publish = self.ably.channels[self.channel].publish

        match = "Need a new token but auth_options does not include a way to request one"
        with pytest.raises(AblyAuthException, match=match):
            await publish('evt', 'msg')

        assert not self.request_token_route.call_count


class TestRenewExpiredToken(BaseAsyncTestCase):

    async def asyncSetUp(self):
        self.test_vars = await TestApp.get_test_vars()
        self.publish_attempts = 0
        self.channel = uuid.uuid4().hex

        self.host = 'fake-host.ably.io'
        key = self.test_vars["keys"][0]['key_name']

        self.base_url = f"https://{self.host}"

        self.request_token_route = responses.post(
            f"{self.base_url}/keys/{key}/requestToken",
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    'token': 'a_token',
                    'expires': int(time.time() * 1000),  # Always expires
                }
            )
        )

        self.time_route = responses.get(
            f"{self.base_url}/time",
            status=200,
            content_type="application/json",
            body=json.dumps(
                [int(time.time() * 1000)]
            )
        )

        def cb_publish(request):
            self.publish_attempts += 1
            if self.publish_fail:
                self.publish_fail = False
                return (
                    401,
                    {},
                    json.dumps(
                        {
                            'error': {'message': 'Authentication failure', 'statusCode': 401, 'code': 40140}
                        }
                    )
                )

            return (
                201,
                {},
                '[]'
            )

        responses.add_callback(
            "POST",
            f"{self.base_url}/channels/{self.channel}/messages",
            callback=cb_publish,
            content_type="application/json"
        )

        responses.start()

    async def asyncTearDown(self):
        responses.stop()
        responses.reset()

    # RSA4b1
    async def test_query_time_false(self):
        ably = await TestApp.get_ably_rest(rest_host=self.host)
        await ably.auth.authorize()
        self.publish_fail = True
        await ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 2
        await ably.close()

    # RSA4b1
    async def test_query_time_true(self):
        ably = await TestApp.get_ably_rest(query_time=True, rest_host=self.host)
        await ably.auth.authorize()
        self.publish_fail = False
        await ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 1
        await ably.close()
