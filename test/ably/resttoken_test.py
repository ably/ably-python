from __future__ import absolute_import

import logging

from mock import patch
import six

from ably import AblyException
from ably import AblyRest
from ably import Capability
from ably.types.tokendetails import TokenDetails
from ably.types.tokenrequest import TokenRequest

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestToken(BaseTestCase):

    def server_time(self):
        return self.ably.time()

    def setUp(self):
        capability = {"*": ["*"]}
        self.permit_all = six.text_type(Capability(capability))
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_request_token_null_params(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token()
        post_time = self.server_time()
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertGreaterEqual(token_details.issued,
                                pre_time,
                                msg="Unexpected issued time")
        self.assertLessEqual(token_details.issued,
                             post_time,
                             msg="Unexpected issued time")
        self.assertEqual(self.permit_all,
                         six.text_type(token_details.capability),
                         msg="Unexpected capability")

    def test_request_token_explicit_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(timestamp=pre_time)
        post_time = self.server_time()
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertGreaterEqual(token_details.issued,
                                pre_time,
                                msg="Unexpected issued time")
        self.assertLessEqual(token_details.issued,
                             post_time,
                             msg="Unexpected issued time")
        self.assertEqual(self.permit_all,
                         six.text_type(Capability(token_details.capability)),
                         msg="Unexpected Capability")

    def test_request_token_explicit_invalid_timestamp(self):
        request_time = self.server_time()
        explicit_timestamp = request_time - 30 * 60 * 1000

        self.assertRaises(AblyException, self.ably.auth.request_token,
                          timestamp=explicit_timestamp)

    def test_request_token_with_system_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(query_time=True)
        post_time = self.server_time()
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertGreaterEqual(token_details.issued,
                                pre_time,
                                msg="Unexpected issued time")
        self.assertLessEqual(token_details.issued,
                             post_time,
                             msg="Unexpected issued time")
        self.assertEqual(self.permit_all,
                         six.text_type(Capability(token_details.capability)),
                         msg="Unexpected Capability")

    def test_request_token_with_duplicate_nonce(self):
        request_time = self.server_time()
        token_details = self.ably.auth.request_token(
            timestamp=request_time,
            nonce='1234567890123456'
        )
        self.assertIsNotNone(token_details.token, msg="Expected token")

        self.assertRaises(AblyException, self.ably.auth.request_token,
                          timestamp=request_time,
                          nonce='1234567890123456')

    def test_request_token_with_capability_that_subsets_key_capability(self):
        capability = Capability({
            "onlythischannel": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(capability=capability)

        self.assertIsNotNone(token_details)
        self.assertIsNotNone(token_details.token)
        self.assertEqual(capability, token_details.capability,
                         msg="Unexpected capability")

    def test_request_token_with_specified_key(self):
        key = RestSetup.get_test_vars()["keys"][1]
        token_details = self.ably.auth.request_token(
            key_name=key["key_name"], key_secret=key["key_secret"])
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertEqual(key.get("capability"),
                         token_details.capability,
                         msg="Unexpected capability")

    @dont_vary_protocol
    def test_request_token_with_invalid_mac(self):
        self.assertRaises(AblyException, self.ably.auth.request_token,
                          mac="thisisnotavalidmac")

    def test_request_token_with_specified_ttl(self):
        token_details = self.ably.auth.request_token(ttl=100)
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertEqual(token_details.issued + 100,
                         token_details.expires, msg="Unexpected expires")

    @dont_vary_protocol
    def test_token_with_excessive_ttl(self):
        excessive_ttl = 365 * 24 * 60 * 60 * 1000
        self.assertRaises(AblyException, self.ably.auth.request_token,
                          ttl=excessive_ttl)

    @dont_vary_protocol
    def test_token_generation_with_invalid_ttl(self):
        self.assertRaises(AblyException, self.ably.auth.request_token,
                          ttl=-1)

    def test_token_generation_with_local_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.request_token()
            self.assertTrue(local_time.called)
            self.assertFalse(server_time.called)

    def test_token_generation_with_server_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.request_token(query_time=True)
            self.assertFalse(local_time.called)
            self.assertTrue(server_time.called)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestCreateTokenRequest(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])
        self.key_name = self.ably.options.key_name
        self.key_secret = self.ably.options.key_secret

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    @dont_vary_protocol
    def test_key_name_and_secret_are_required(self):
        self.assertRaisesRegexp(AblyException, "40101 401 No key specified",
                                self.ably.auth.create_token_request)
        self.assertRaisesRegexp(AblyException, "40101 401 No key specified",
                                self.ably.auth.create_token_request,
                                key_name=self.key_name)
        self.assertRaisesRegexp(AblyException, "40101 401 No key specified",
                                self.ably.auth.create_token_request,
                                key_secret=self.key_secret)

    @dont_vary_protocol
    def test_with_local_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.create_token_request(
                key_name=self.key_name, key_secret=self.key_secret, query_time=False)
            self.assertTrue(local_time.called)
            self.assertFalse(server_time.called)

    @dont_vary_protocol
    def test_with_server_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.create_token_request(
                key_name=self.key_name, key_secret=self.key_secret, query_time=True)
            self.assertTrue(server_time.called)
            self.assertFalse(local_time.called)

    def test_token_request_can_be_used_to_get_a_token(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        self.assertIsInstance(token_request, TokenRequest)

        def auth_callback(**kwargs):
            return token_request

        ably = AblyRest(auth_callback=auth_callback,
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_binary_protocol=self.use_binary_protocol)

        token = ably.auth.authorise()

        self.assertIsInstance(token, TokenDetails)

    @dont_vary_protocol
    def test_nonce_is_random_and_longer_than_15_characters(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        self.assertGreater(len(token_request.nonce), 15)

        another_token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        self.assertGreater(len(another_token_request.nonce), 15)

        self.assertNotEqual(token_request.nonce, another_token_request.nonce)

    @dont_vary_protocol
    def test_ttl_is_optional_and_specified_in_ms(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        self.assertEquals(
            token_request.ttl, TokenDetails.DEFAULTS['ttl'] * 1000)

    @dont_vary_protocol
    def test_accept_all_token_params(self):
        token_params = {
            'ttl': 1000,
            'capability': Capability({'channel': ['publish']}),
            'client_id': 'a_id',
            'timestamp': 1000,
            'nonce': 'a_nonce',
        }
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret,
            **token_params
        )
        self.assertEqual(token_request.ttl, token_params['ttl'])
        self.assertEqual(token_request.capability, str(token_params['capability']))
        self.assertEqual(token_request.client_id, token_params['client_id'])
        self.assertEqual(token_request.timestamp, token_params['timestamp'])
        self.assertEqual(token_request.nonce, token_params['nonce'])

    def test_capability(self):
        capability = Capability({'channel': ['publish']})
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret,
            capability=capability)
        self.assertEqual(token_request.capability, str(capability))

        def auth_callback(**kwargs):
            return token_request

        ably = AblyRest(auth_callback=auth_callback,
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_binary_protocol=self.use_binary_protocol)

        token = ably.auth.authorise()

        self.assertEqual(str(token.capability), str(capability))

    @dont_vary_protocol
    def test_hmac(self):
        ably = AblyRest(key_name='a_key_name', key_secret='a_secret')
        params = {
            'key_name': 'a_key_name',
            'ttl': 1000,
            'nonce': 'abcde100',
            'client_id': 'a_id',
            'timestamp': 1000,
        }
        token_request = ably.auth.create_token_request(
            key_secret='a_secret', **params)
        self.assertEqual(
            token_request.mac, 'sYkCH0Un+WgzI7/Nhy0BoQIKq9HmjKynCRs4E3qAbGQ=')
