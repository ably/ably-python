from __future__ import absolute_import

import unittest

import six
from mock import patch

from ably import AblyRest
from ably import AblyException
from ably.transport.defaults import Defaults

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol

test_vars = RestSetup.get_test_vars()


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestInit(unittest.TestCase):
    @dont_vary_protocol
    def test_key_only(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"])
        self.assertEqual(ably.options.key_name, test_vars["keys"][0]["key_name"],
                         "Key name does not match")
        self.assertEqual(ably.options.key_secret, test_vars["keys"][0]["key_secret"],
                         "Key secret does not match")

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    @dont_vary_protocol
    def test_with_token(self):
        ably = AblyRest(token="foo")
        self.assertEqual(ably.options.auth_token, "foo",
                         "Token not set at options")
    @dont_vary_protocol
    def test_with_options_token_callback(self):
        def token_callback(**params):
            return "this_is_not_really_a_token_request"
        AblyRest(auth_callback=token_callback)

    @dont_vary_protocol
    def test_ambiguous_key_raises_value_error(self):
        self.assertRaisesRegexp(ValueError, "mutually exclusive", AblyRest,
                                key=test_vars["keys"][0]["key_str"],
                                key_name='x')
        self.assertRaisesRegexp(ValueError, "mutually exclusive", AblyRest,
                                key=test_vars["keys"][0]["key_str"],
                                key_secret='x')

    @dont_vary_protocol
    def test_with_key_name_or_secret_only(self):
        self.assertRaisesRegexp(ValueError, "key is missing", AblyRest,
                                key_name='x')
        self.assertRaisesRegexp(ValueError, "key is missing", AblyRest,
                                key_secret='x')

    @dont_vary_protocol
    def test_with_key_name_and_secret(self):
        ably = AblyRest(key_name="foo", key_secret="bar")
        self.assertEqual(ably.options.key_name, "foo",
                         "Key name does not match")
        self.assertEqual(ably.options.key_secret, "bar",
                         "Key secret does not match")

    @dont_vary_protocol
    def test_with_options_auth_url(self):
        AblyRest(auth_url='not_really_an_url')

    @dont_vary_protocol
    def test_specified_host(self):
        ably = AblyRest(token='foo', host="some.other.host")
        self.assertEqual("some.other.host", ably.options.host,
                         msg="Unexpected host mismatch")

    @dont_vary_protocol
    def test_specified_port(self):
        ably = AblyRest(token='foo', port=9998, tls_port=9999)
        self.assertEqual(9999, Defaults.get_port(ably.options),
                         msg="Unexpected port mismatch. Expected: 9999. Actual: %d" %
                         ably.options.tls_port)

    @dont_vary_protocol
    def test_tls_defaults_to_true(self):
        ably = AblyRest(token='foo')
        self.assertTrue(ably.options.tls,
                        msg="Expected encryption to default to true")
        self.assertEqual(Defaults.tls_port, Defaults.get_port(ably.options),
                         msg="Unexpected port mismatch")

    @dont_vary_protocol
    def test_tls_can_be_disabled(self):
        ably = AblyRest(token='foo', tls=False)
        self.assertFalse(ably.options.tls,
                         msg="Expected encryption to be False")
        self.assertEqual(Defaults.port, Defaults.get_port(ably.options),
                         msg="Unexpected port mismatch")

    @dont_vary_protocol
    def test_with_no_params(self):
        self.assertRaises(ValueError, AblyRest)

    @dont_vary_protocol
    def test_with_no_auth_params(self):
        self.assertRaises(ValueError, AblyRest, port=111)

    def test_query_time_param(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"], query_time=True,
                        use_binary_protocol=self.use_binary_protocol)

        timestamp = ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            ably.auth.request_token()
            self.assertFalse(local_time.called)
            self.assertTrue(server_time.called)

    @dont_vary_protocol
    def test_requests_over_https_production(self):
        ably = AblyRest(token='token')
        self.assertEquals('https://rest.ably.io',
                          '{0}://{1}'.format(
                            ably.http.preferred_scheme,
                            ably.http.preferred_host))
        self.assertEqual(ably.http.preferred_port, 443)

    @dont_vary_protocol
    def test_requests_over_http_production(self):
        ably = AblyRest(token='token', tls=False)
        self.assertEquals('http://rest.ably.io',
                          '{0}://{1}'.format(
                            ably.http.preferred_scheme,
                            ably.http.preferred_host))
        self.assertEqual(ably.http.preferred_port, 80)

    @dont_vary_protocol
    def test_request_basic_auth_over_http_fails(self):
        ably = AblyRest(key_secret='foo', key_name='bar', tls=False)

        with self.assertRaises(AblyException) as cm:
            ably.http.get('/time', skip_auth=False)

        self.assertEqual(401, cm.exception.status_code)
        self.assertEqual(40103, cm.exception.code)
        self.assertEqual('Cannot use Basic Auth over non-TLS connections',
                         cm.exception.message)

if __name__ == "__main__":
    unittest.main()
