from __future__ import absolute_import

import logging
import time
import json
import uuid
import base64
import responses

import mock
import six
from requests import Session

from ably import AblyRest
from ably import Auth
from ably import AblyException
from ably.types.tokendetails import TokenDetails

from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase, VaryByProtocolTestsMetaclass, dont_vary_protocol

test_vars = RestSetup.get_test_vars()


log = logging.getLogger(__name__)


# does not make any request, no need to vary by protocol
class TestAuth(BaseTestCase):

    def test_auth_init_key_only(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"])
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_mechanism,
                         msg="Unexpected Auth method mismatch")
        self.assertEqual(ably.auth.auth_options.key_name,
                         test_vars["keys"][0]['key_name'])
        self.assertEqual(ably.auth.auth_options.key_secret,
                         test_vars["keys"][0]['key_secret'])

    def test_auth_init_token_only(self):
        ably = AblyRest(token="this_is_not_really_a_token")

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_mechanism,
                         msg="Unexpected Auth method mismatch")

    def test_auth_token_details(self):
        td = TokenDetails()
        ably = AblyRest(token_details=td)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_mechanism)
        self.assertIs(ably.auth.token_details, td)

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(**params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        ably = AblyRest(key_name=test_vars["keys"][0]["key_name"],
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        auth_callback=token_callback)

        try:
            ably.stats(None)
        except:
            pass

        self.assertTrue(callback_called, msg="Token callback not called")
        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_mechanism,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_key_and_client_id(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"], client_id='testClientId')

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_mechanism,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token(self):

        ably = AblyRest(token="this_is_not_really_a_token",
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"])

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_mechanism,
                msg="Unexpected Auth method mismatch")

    @responses.activate
    def test_auth_with_url_method_headers_and_params(self):
        url = 'http://www.example.com'
        headers = {'foo': 'bar'}
        self.ably = AblyRest(auth_url=url,
                             auth_method='POST',
                             auth_headers=headers,
                             auth_params={'spam': 'eggs'},
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

        responses.add(responses.POST, url, body='token_string')
        token_details = self.ably.auth.request_token()
        self.assertIsInstance(token_details, TokenDetails)
        self.assertEquals(len(responses.calls), 1)
        self.assertEquals(headers['foo'],
                          responses.calls[0].request.headers['foo'])
        self.assertTrue(responses.calls[0].request.url.endswith('?spam=eggs'))

    def test_request_basic_auth_header(self):
        ably = AblyRest(key_secret='foo', key_name='bar')

        with mock.patch.object(Session, 'prepare_request') as get_mock:
            try:
                ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        self.assertEqual(authorization,
                         'Basic %s' %
                         base64.b64encode('bar:foo'.encode('ascii')
                                          ).decode('utf-8'))

    def test_request_token_auth_header(self):
        ably = AblyRest(token='not_a_real_token')

        with mock.patch.object(Session, 'prepare_request') as get_mock:
            try:
                ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        self.assertEqual(authorization,
                         'Bearer %s' %
                         base64.b64encode('not_a_real_token'.encode('ascii')
                                          ).decode('utf-8'))

    def test_if_cant_authenticate_via_token(self):
        self.assertRaises(ValueError, AblyRest, use_token_auth=True)

    def test_use_auth_token(self):
        ably = AblyRest(use_token_auth=True, key=test_vars["keys"][0]["key_str"])
        self.assertEquals(ably.auth.auth_mechanism, Auth.Method.TOKEN)

    def test_with_client_id(self):
        ably = AblyRest(client_id='client_id', key=test_vars["keys"][0]["key_str"])
        self.assertEquals(ably.auth.auth_mechanism, Auth.Method.TOKEN)

    def test_with_auth_url(self):
        ably = AblyRest(auth_url='auth_url')
        self.assertEquals(ably.auth.auth_mechanism, Auth.Method.TOKEN)

    def test_with_auth_callback(self):
        ably = AblyRest(auth_callback=lambda x: x)
        self.assertEquals(ably.auth.auth_mechanism, Auth.Method.TOKEN)

    def test_with_token(self):
        ably = AblyRest(token='a token')
        self.assertEquals(ably.auth.auth_mechanism, Auth.Method.TOKEN)

    def test_default_ttl_is_1hour(self):
        one_hour_in_seconds = 60 * 60
        self.assertEquals(TokenDetails.DEFAULTS['ttl'], one_hour_in_seconds)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestAuthAuthorize(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_if_authorize_changes_auth_mechanism_to_token(self):

        self.assertEqual(Auth.Method.BASIC, self.ably.auth.auth_mechanism,
                         msg="Unexpected Auth method mismatch")

        self.ably.auth.authorise()

        self.assertEqual(Auth.Method.TOKEN, self.ably.auth.auth_mechanism,
                         msg="Authorise should change the Auth method")

    def test_authorize_shouldnt_create_token_if_not_expired(self):

        token = self.ably.auth.authorise()

        new_token = self.ably.auth.authorise()

        self.assertGreater(token.expires, time.time()*1000)

        self.assertIs(new_token, token)

    def test_authorize_should_create_new_token_if_forced(self):

        token = self.ably.auth.authorise()

        new_token = self.ably.auth.authorise(force=True)

        self.assertGreater(token.expires, time.time()*1000)

        self.assertIsNot(new_token, token)
        self.assertGreater(new_token.expires, token.expires)

    def test_authorize_create_new_token_if_expired(self):

        token = self.ably.auth.authorise()

        with mock.patch('ably.types.tokendetails.TokenDetails.expires',
                        new_callable=mock.PropertyMock(return_value=42)):
            new_token = self.ably.auth.authorise()

        self.assertIsNot(token, new_token)

    def test_authorize_returns_a_token_details(self):

        token = self.ably.auth.authorise()

        self.assertIsInstance(token, TokenDetails)

    @dont_vary_protocol
    def test_authorize_adhere_to_request_token(self):
        with mock.patch('ably.rest.auth.Auth.request_token') as request_mock:
            self.ably.auth.authorise(force=True, ttl=10, client_id='client_id',
                                     auth_url='somewhere.com', query_time=True)

        request_mock.assert_called_once_with(ttl=10, client_id='client_id',
                                             auth_url='somewhere.com',
                                             query_time=True)

    def test_with_token_str_https(self):
        token = self.ably.auth.authorise()
        token = token.token
        ably = AblyRest(token=token, rest_host=test_vars["host"],
                        port=test_vars["port"], tls_port=test_vars["tls_port"],
                        tls=True, use_binary_protocol=self.use_binary_protocol)
        ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')

    def test_with_token_str_http(self):
        token = self.ably.auth.authorise()
        token = token.token
        ably = AblyRest(token=token, rest_host=test_vars["host"],
                        port=test_vars["port"], tls_port=test_vars["tls_port"],
                        tls=False, use_binary_protocol=self.use_binary_protocol)
        ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRequestToken(BaseTestCase):

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    def test_with_key(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"],
                             use_binary_protocol=self.use_binary_protocol)

        token_details = self.ably.auth.request_token()
        self.assertIsInstance(token_details, TokenDetails)

        ably = AblyRest(token_details=token_details,
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_binary_protocol=self.use_binary_protocol)
        channel = self.protocol_channel_name('test_request_token_with_key')

        ably.channels[channel].publish('event', 'foo')

        self.assertEqual(ably.channels[channel].history().items[0].data, 'foo')

    @dont_vary_protocol
    @responses.activate
    def test_with_url(self):
        url = 'http://www.example.com'
        headers = {'foo': 'bar'}
        self.ably = AblyRest(auth_url=url,
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

        responses.add(responses.POST, url, body='token_string')
        token_details = self.ably.auth.request_token(auth_url=url,
                                                     auth_headers=headers,
                                                     auth_method='POST',
                                                     auth_params={'spam':
                                                                  'eggs'})
        self.assertIsInstance(token_details, TokenDetails)
        self.assertEquals(len(responses.calls), 1)
        self.assertEquals(headers['foo'],
                          responses.calls[0].request.headers['foo'])
        self.assertTrue(responses.calls[0].request.url.endswith('?spam=eggs'))
        self.assertEquals('token_string', token_details.token)

        responses.reset()
        responses.add(responses.GET, url, json={'issued': 1, 'token':
                                                'another_token_string'})
        token_details = self.ably.auth.request_token(auth_url=url)
        self.assertEquals('another_token_string', token_details.token)

    @dont_vary_protocol
    def test_with_callback(self):
        def callback(ttl, capability, client_id, timestamp):
            return 'token_string'

        self.ably = AblyRest(auth_callback=callback,
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

        token_details = self.ably.auth.request_token(auth_callback=callback)
        self.assertIsInstance(token_details, TokenDetails)
        self.assertEquals('token_string', token_details.token)

        def callback(ttl, capability, client_id, timestamp):
            return TokenDetails(token='another_token_string')

        token_details = self.ably.auth.request_token(auth_callback=callback)
        self.assertEquals('another_token_string', token_details.token)

    @dont_vary_protocol
    @responses.activate
    def test_when_auth_url_has_query_string(self):
        url = 'http://www.example.com?with=query'
        headers = {'foo': 'bar'}
        self.ably = AblyRest(auth_url=url,
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

        responses.add(responses.POST, 'http://www.example.com',
                      body='token_string')
        self.ably.auth.request_token(auth_url=url,
                                     auth_headers=headers,
                                     auth_method='POST',
                                     auth_params={'spam':
                                                  'eggs'})
        self.assertTrue(responses.calls[0].request.url.endswith(
                            '?with=query&spam=eggs'))


class TestRenewToken(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"],
                             use_binary_protocol=False)
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
            'https://sandbox-rest.ably.io:443/keys/{}/requestToken'.format(
                test_vars["keys"][0]['key_name']),
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
            'https://sandbox-rest.ably.io:443/channels/{}/publish'.format(
                self.channel),
            call_back)
        responses.start()

    def tearDown(self):
        responses.stop()
        responses.reset()

    def test_when_renewable(self):
        self.ably.auth.authorise()
        self.ably.channels[self.channel].publish('evt', 'msg')
        self.assertEquals(1, self.token_requests)
        self.assertEquals(1, self.publish_attempts)

        # Triggers an authentication 401 failure which should automatically request a new token
        self.ably.channels[self.channel].publish('evt', 'msg')
        self.assertEquals(2, self.token_requests)
        self.assertEquals(3, self.publish_attempts)

    def test_when_not_renewable(self):
        self.ably = AblyRest(token='token ID cannot be used to create a new token',
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"],
                             use_binary_protocol=False)
        self.ably.channels[self.channel].publish('evt', 'msg')
        self.assertEquals(1, self.publish_attempts)

        publish = self.ably.channels[self.channel].publish

        self.assertRaisesRegexp(AblyException, "No key specified", publish,
                                'evt', 'msg')
        self.assertEquals(0, self.token_requests)

    def test_when_not_renewable_with_token_details(self):
        token_details = TokenDetails(token='a_dummy_token')
        self.ably = AblyRest(
            token_details=token_details,
            rest_host=test_vars["host"],
            port=test_vars["port"],
            tls_port=test_vars["tls_port"],
            tls=test_vars["tls"],
            use_binary_protocol=False)
        self.ably.channels[self.channel].publish('evt', 'msg')
        self.assertEquals(1, self.publish_attempts)

        publish = self.ably.channels[self.channel].publish

        self.assertRaisesRegexp(AblyException, "No key specified", publish,
                                'evt', 'msg')
        self.assertEquals(0, self.token_requests)
