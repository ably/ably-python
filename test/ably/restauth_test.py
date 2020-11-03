import logging
import time
import json
import uuid
import base64
import responses
import warnings
from urllib.parse import parse_qs, urlparse

import mock
import pytest
from requests import Session

import ably
from ably import AblyRest
from ably import Auth
from ably import AblyAuthException
from ably.types.tokendetails import TokenDetails

from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase, VaryByProtocolTestsMetaclass, dont_vary_protocol

test_vars = RestSetup.get_test_vars()


log = logging.getLogger(__name__)


# does not make any request, no need to vary by protocol
class TestAuth(BaseTestCase):

    def test_auth_init_key_only(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"])
        assert Auth.Method.BASIC == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.auth_options.key_name == test_vars["keys"][0]['key_name']
        assert ably.auth.auth_options.key_secret == test_vars["keys"][0]['key_secret']

    def test_auth_init_token_only(self):
        ably = AblyRest(token="this_is_not_really_a_token")

        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    def test_auth_token_details(self):
        td = TokenDetails()
        ably = AblyRest(token_details=td)

        assert Auth.Method.TOKEN == ably.auth.auth_mechanism
        assert ably.auth.token_details is td

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(token_params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        ably = RestSetup.get_ably_rest(
            key=None,
            key_name=test_vars["keys"][0]["key_name"],
            auth_callback=token_callback)

        try:
            ably.stats(None)
        except Exception:
            pass

        assert callback_called, "Token callback not called"
        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    def test_auth_init_with_key_and_client_id(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"], client_id='testClientId')

        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"
        assert ably.auth.client_id == 'testClientId'

    def test_auth_init_with_token(self):
        ably = RestSetup.get_ably_rest(key=None, token="this_is_not_really_a_token")
        assert Auth.Method.TOKEN == ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

    # RSA11
    def test_request_basic_auth_header(self):
        ably = AblyRest(key_secret='foo', key_name='bar')

        with mock.patch.object(Session, 'prepare_request') as get_mock:
            try:
                ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        assert authorization == 'Basic %s' % base64.b64encode('bar:foo'.encode('ascii')).decode('utf-8')

    def test_request_token_auth_header(self):
        ably = AblyRest(token='not_a_real_token')

        with mock.patch.object(Session, 'prepare_request') as get_mock:
            try:
                ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        assert authorization == 'Bearer %s' % base64.b64encode('not_a_real_token'.encode('ascii')).decode('utf-8')

    def test_if_cant_authenticate_via_token(self):
        with pytest.raises(ValueError):
            AblyRest(use_token_auth=True)

    def test_use_auth_token(self):
        ably = AblyRest(use_token_auth=True, key=test_vars["keys"][0]["key_str"])
        assert ably.auth.auth_mechanism == Auth.Method.TOKEN

    def test_with_client_id(self):
        ably = AblyRest(client_id='client_id', key=test_vars["keys"][0]["key_str"])
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
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        default_token_params={'ttl': 12345})
        assert ably.auth.auth_options.default_token_params == {'ttl': 12345}


class TestAuthAuthorize(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def setUp(self):
        self.ably = RestSetup.get_ably_rest()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_if_authorize_changes_auth_mechanism_to_token(self):

        assert Auth.Method.BASIC == self.ably.auth.auth_mechanism, "Unexpected Auth method mismatch"

        self.ably.auth.authorize()

        assert Auth.Method.TOKEN == self.ably.auth.auth_mechanism, "Authorise should change the Auth method"

    # RSA10a
    @dont_vary_protocol
    def test_authorize_always_creates_new_token(self):
        self.ably.auth.authorize({'capability': {'test': ['publish']}})
        self.ably.channels.test.publish('event', 'data')

        self.ably.auth.authorize({'capability': {'test': ['subscribe']}})
        with pytest.raises(AblyAuthException):
            self.ably.channels.test.publish('event', 'data')

    def test_authorize_create_new_token_if_expired(self):
        token = self.ably.auth.authorize()
        with mock.patch('ably.rest.auth.Auth.token_details_has_expired',
                        return_value=True):
            new_token = self.ably.auth.authorize()

        assert token is not new_token

    def test_authorize_returns_a_token_details(self):
        token = self.ably.auth.authorize()
        assert isinstance(token, TokenDetails)

    @dont_vary_protocol
    def test_authorize_adheres_to_request_token(self):
        token_params = {'ttl': 10, 'client_id': 'client_id'}
        auth_params = {'auth_url': 'somewhere.com', 'query_time': True}
        with mock.patch('ably.rest.auth.Auth.request_token') as request_mock:
            self.ably.auth.authorize(token_params, auth_params)

        token_called, auth_called = request_mock.call_args
        assert token_called[0] == token_params

        # Authorise may call request_token with some default auth_options.
        for arg, value in auth_params.items():
            assert auth_called[arg] == value, "%s called with wrong value: %s" % (arg, value)

    def test_with_token_str_https(self):
        token = self.ably.auth.authorize()
        token = token.token
        ably = RestSetup.get_ably_rest(key=None, token=token, tls=True,
                                       use_binary_protocol=self.use_binary_protocol)
        ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')

    def test_with_token_str_http(self):
        token = self.ably.auth.authorize()
        token = token.token
        ably = RestSetup.get_ably_rest(key=None, token=token, tls=False,
                                       use_binary_protocol=self.use_binary_protocol)
        ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')

    def test_if_default_client_id_is_used(self):
        ably = RestSetup.get_ably_rest(client_id='my_client_id',
                                       use_binary_protocol=self.use_binary_protocol)
        token = ably.auth.authorize()
        assert token.client_id == 'my_client_id'

    # RSA10j
    def test_if_parameters_are_stored_and_used_as_defaults(self):
        # Define some parameters
        auth_options = dict(self.ably.auth.auth_options.auth_options)
        auth_options['auth_headers'] = {'a_headers': 'a_value'}
        self.ably.auth.authorize({'ttl': 555}, auth_options)
        with mock.patch('ably.rest.auth.Auth.request_token',
                        wraps=self.ably.auth.request_token) as request_mock:
            self.ably.auth.authorize()

        token_called, auth_called = request_mock.call_args
        assert token_called[0] == {'ttl': 555}
        assert auth_called['auth_headers'] == {'a_headers': 'a_value'}

        # Different parameters, should completely replace the first ones, not merge
        auth_options = dict(self.ably.auth.auth_options.auth_options)
        auth_options['auth_headers'] = None
        self.ably.auth.authorize({}, auth_options)
        with mock.patch('ably.rest.auth.Auth.request_token',
                        wraps=self.ably.auth.request_token) as request_mock:
            self.ably.auth.authorize()

        token_called, auth_called = request_mock.call_args
        assert token_called[0] == {}
        assert auth_called['auth_headers'] is None

    # RSA10g
    def test_timestamp_is_not_stored(self):
        # authorize once with arbitrary defaults
        auth_options = dict(self.ably.auth.auth_options.auth_options)
        auth_options['auth_headers'] = {'a_headers': 'a_value'}
        token_1 = self.ably.auth.authorize(
            {'ttl': 60 * 1000, 'client_id': 'new_id'},
            auth_options)
        assert isinstance(token_1, TokenDetails)

        # call authorize again with timestamp set
        timestamp = self.ably.time()
        with mock.patch('ably.rest.auth.TokenRequest',
                        wraps=ably.types.tokenrequest.TokenRequest) as tr_mock:
            auth_options = dict(self.ably.auth.auth_options.auth_options)
            auth_options['auth_headers'] = {'a_headers': 'a_value'}
            token_2 = self.ably.auth.authorize(
                {'ttl': 60 * 1000, 'client_id': 'new_id', 'timestamp': timestamp},
                auth_options)
        assert isinstance(token_2, TokenDetails)
        assert token_1 != token_2
        assert tr_mock.call_args[1]['timestamp'] == timestamp

        # call authorize again with no params
        with mock.patch('ably.rest.auth.TokenRequest',
                        wraps=ably.types.tokenrequest.TokenRequest) as tr_mock:
            token_4 = self.ably.auth.authorize()
        assert isinstance(token_4, TokenDetails)
        assert token_2 != token_4
        assert tr_mock.call_args[1]['timestamp'] != timestamp

    def test_client_id_precedence(self):
        client_id = uuid.uuid4().hex
        overridden_client_id = uuid.uuid4().hex
        ably = RestSetup.get_ably_rest(
            use_binary_protocol=self.use_binary_protocol,
            client_id=client_id,
            default_token_params={'client_id': overridden_client_id})
        token = ably.auth.authorize()
        assert token.client_id == client_id
        assert ably.auth.client_id == client_id

        channel = ably.channels[
            self.get_channel_name('test_client_id_precedence')]
        channel.publish('test', 'data')
        assert channel.history().items[0].client_id == client_id

    # RSA10l
    @dont_vary_protocol
    def test_authorise(self):
        with warnings.catch_warnings(record=True) as ws:
            # Cause all warnings to always be triggered
            warnings.simplefilter("always")

            token = self.ably.auth.authorise()
            assert isinstance(token, TokenDetails)

            # Verify warning is raised
            ws = [w for w in ws if issubclass(w.category, DeprecationWarning)]
            assert len(ws) == 1


class TestRequestToken(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    def test_with_key(self):
        self.ably = RestSetup.get_ably_rest(use_binary_protocol=self.use_binary_protocol)

        token_details = self.ably.auth.request_token()
        assert isinstance(token_details, TokenDetails)

        ably = RestSetup.get_ably_rest(key=None, token_details=token_details,
                                       use_binary_protocol=self.use_binary_protocol)
        channel = self.get_channel_name('test_request_token_with_key')

        ably.channels[channel].publish('event', 'foo')

        assert ably.channels[channel].history().items[0].data == 'foo'

    @dont_vary_protocol
    @responses.activate
    def test_with_auth_url_headers_and_params_POST(self):
        url = 'http://www.example.com'
        headers = {'foo': 'bar'}
        self.ably = RestSetup.get_ably_rest(key=None, auth_url=url)

        auth_params = {'foo': 'auth', 'spam': 'eggs'}
        token_params = {'foo': 'token'}

        responses.add(responses.POST, url, body='token_string')
        token_details = self.ably.auth.request_token(
            token_params=token_params, auth_url=url, auth_headers=headers,
            auth_method='POST', auth_params=auth_params)

        assert isinstance(token_details, TokenDetails)
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert request.headers['content-type'] == 'application/x-www-form-urlencoded'
        assert headers['foo'] == request.headers['foo']
        assert urlparse(request.url).query == ''  # No querystring!
        assert parse_qs(request.body) == {'foo': ['token'], 'spam': ['eggs']}  # TokenParams has precedence
        assert 'token_string' == token_details.token

    @dont_vary_protocol
    @responses.activate
    def test_with_auth_url_headers_and_params_GET(self):

        url = 'http://www.example.com'
        headers = {'foo': 'bar'}
        self.ably = RestSetup.get_ably_rest(
            key=None, auth_url=url,
            auth_headers={'this': 'will_not_be_used'},
            auth_params={'this': 'will_not_be_used'})

        auth_params = {'foo': 'auth', 'spam': 'eggs'}
        token_params = {'foo': 'token'}

        responses.add(responses.GET, url, json={'issued': 1, 'token':
                                                'another_token_string'})
        token_details = self.ably.auth.request_token(
            token_params=token_params, auth_url=url, auth_headers=headers,
            auth_params=auth_params)
        assert 'another_token_string' == token_details.token
        request = responses.calls[0].request
        assert request.headers['foo'] == 'bar'
        assert 'this' not in request.headers
        assert parse_qs(urlparse(request.url).query) == {'foo': ['token'], 'spam': ['eggs']}
        assert not request.body

    @dont_vary_protocol
    def test_with_callback(self):
        called_token_params = {'ttl': '3600000'}
        def callback(token_params):
            assert token_params == called_token_params
            return 'token_string'

        self.ably = RestSetup.get_ably_rest(key=None, auth_callback=callback)

        token_details = self.ably.auth.request_token(
            token_params=called_token_params, auth_callback=callback)
        assert isinstance(token_details, TokenDetails)
        assert 'token_string' == token_details.token

        def callback(token_params):
            assert token_params == called_token_params
            return TokenDetails(token='another_token_string')

        token_details = self.ably.auth.request_token(
            token_params=called_token_params, auth_callback=callback)
        assert 'another_token_string' == token_details.token

    @dont_vary_protocol
    @responses.activate
    def test_when_auth_url_has_query_string(self):
        url = 'http://www.example.com?with=query'
        headers = {'foo': 'bar'}
        self.ably = RestSetup.get_ably_rest(key=None, auth_url=url)

        responses.add(responses.GET, 'http://www.example.com',
                      body='token_string')
        self.ably.auth.request_token(auth_url=url,
                                     auth_headers=headers,
                                     auth_params={'spam': 'eggs'})
        assert responses.calls[0].request.url.endswith('?with=query&spam=eggs')

    @dont_vary_protocol
    def test_client_id_null_for_anonymous_auth(self):
        ably = RestSetup.get_ably_rest(
            key=None,
            key_name=test_vars["keys"][0]["key_name"],
            key_secret=test_vars["keys"][0]["key_secret"])
        token = ably.auth.authorize()

        assert isinstance(token, TokenDetails)
        assert token.client_id is None
        assert ably.auth.client_id is None

    @dont_vary_protocol
    def test_client_id_null_until_auth(self):
        client_id = uuid.uuid4().hex
        token_ably = RestSetup.get_ably_rest(
            default_token_params={'client_id': client_id})
        # before auth, client_id is None
        assert token_ably.auth.client_id is None

        token = token_ably.auth.authorize()
        assert isinstance(token, TokenDetails)

        # after auth, client_id is defined
        assert token.client_id == client_id
        assert token_ably.auth.client_id == client_id


class TestRenewToken(BaseTestCase):

    def setUp(self):
        host = test_vars['host']
        self.ably = RestSetup.get_ably_rest(use_binary_protocol=False)
        # with headers
        self.token_requests = 0
        self.publish_attempts = 0
        self.tokens = ['a_token', 'another_token']
        self.channel = uuid.uuid4().hex

        def call_back(request):
            headers = {'Content-Type': 'application/json'}
            body = {}
            self.token_requests += 1
            body['token'] = self.tokens[self.token_requests - 1]
            body['expires'] = (time.time() + 60) * 1000
            return (200, headers, json.dumps(body))

        responses.add_callback(
            responses.POST,
            'https://{}:443/keys/{}/requestToken'.format(
                host, test_vars["keys"][0]['key_name']),
            call_back)

        def call_back(request):
            headers = {'Content-Type': 'application/json'}
            self.publish_attempts += 1
            if self.publish_attempts in [1, 3]:
                body = '[]'
                status = 201
            else:
                body = {'error': {'message': 'Authentication failure', 'statusCode': 401, 'code': 40140}}
                status = 401

            return (status, headers, json.dumps(body))

        responses.add_callback(
            responses.POST,
            'https://{}:443/channels/{}/messages'.format(host, self.channel),
            call_back)
        responses.start()

    def tearDown(self):
        responses.stop()
        responses.reset()

    # RSA4b
    def test_when_renewable(self):
        self.ably.auth.authorize()
        self.ably.channels[self.channel].publish('evt', 'msg')
        assert 1 == self.token_requests
        assert 1 == self.publish_attempts

        # Triggers an authentication 401 failure which should automatically request a new token
        self.ably.channels[self.channel].publish('evt', 'msg')
        assert 2 == self.token_requests
        assert 3 == self.publish_attempts

    # RSA4a
    def test_when_not_renewable(self):
        self.ably = RestSetup.get_ably_rest(
            key=None,
            token='token ID cannot be used to create a new token',
            use_binary_protocol=False)
        self.ably.channels[self.channel].publish('evt', 'msg')
        assert 1 == self.publish_attempts

        publish = self.ably.channels[self.channel].publish

        match = "The provided token is not renewable and there is no means to generate a new token"
        with pytest.raises(AblyAuthException, match=match):
            publish('evt', 'msg')

        assert 0 == self.token_requests

    # RSA4a
    def test_when_not_renewable_with_token_details(self):
        token_details = TokenDetails(token='a_dummy_token')
        self.ably = RestSetup.get_ably_rest(
            key=None,
            token_details=token_details,
            use_binary_protocol=False)
        self.ably.channels[self.channel].publish('evt', 'msg')
        assert 1 == self.publish_attempts

        publish = self.ably.channels[self.channel].publish

        match = "The provided token is not renewable and there is no means to generate a new token"
        with pytest.raises(AblyAuthException, match=match):
            publish('evt', 'msg')

        assert 0 == self.token_requests


class TestRenewExpiredToken(BaseTestCase):

    def setUp(self):
        self.publish_attempts = 0
        self.channel = uuid.uuid4().hex

        host = test_vars['host']
        key = test_vars["keys"][0]['key_name']
        base_url = 'https://{}:443'.format(host)
        headers = {'Content-Type': 'application/json'}

        def cb_request_token(request):
            body = {
                'token': 'a_token',
                'expires': int(time.time() * 1000),  # Always expires
            }
            return (200, headers, json.dumps(body))

        def cb_publish(request):
            self.publish_attempts += 1
            if self.publish_fail:
                self.publish_fail = False
                body = {'error': {'message': 'Authentication failure', 'statusCode': 401, 'code': 40140}}
                status = 401
            else:
                body = '[]'
                status = 201

            return (status, headers, json.dumps(body))

        def cb_time(request):
            body = [int(time.time() * 1000)]
            return (200, headers, json.dumps(body))

        add_callback = responses.add_callback
        add_callback(responses.POST, '{}/keys/{}/requestToken'.format(base_url, key), cb_request_token)
        add_callback(responses.POST, '{}/channels/{}/messages'.format(base_url, self.channel), cb_publish)
        add_callback(responses.GET, '{}/time'.format(base_url), cb_time)

        responses.start()

    def tearDown(self):
        responses.stop()
        responses.reset()

    # RSA4b1
    def test_query_time_false(self):
        ably = RestSetup.get_ably_rest()
        ably.auth.authorize()
        self.publish_fail = True
        ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 2

    # RSA4b1
    def test_query_time_true(self):
        ably = RestSetup.get_ably_rest(query_time=True)
        ably.auth.authorize()
        self.publish_fail = False
        ably.channels[self.channel].publish('evt', 'msg')
        assert self.publish_attempts == 1
