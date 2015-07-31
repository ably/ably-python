from __future__ import absolute_import

import unittest

from ably import AblyRest
from ably import AblyException
from ably import Options
from ably.transport.defaults import Defaults

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestInit(unittest.TestCase):
    def test_key_only(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"])
        self.assertEqual(ably.options.key_id, test_vars["keys"][0]["key_id"],
                         "Key id does not match")
        self.assertEqual(ably.options.key_value, test_vars["keys"][0]["key_value"],
                         "Key value does not match")

    def test_key_in_options(self):
        ably = AblyRest(options=Options(key=test_vars["keys"][0]["key_str"]))
        self.assertEqual(ably.options.key_id, test_vars["keys"][0]["key_id"],
                         "Key id does not match")
        self.assertEqual(ably.options.key_value, test_vars["keys"][0]["key_value"],
                         "Key value does not match")

    def test_token_in_options(self):
        ably = AblyRest(options=Options(auth_token='foo'))
        self.assertEqual(ably.options.auth_token, 'foo',
                         "Token not set at options")

    def test_with_token(self):
        ably = AblyRest(token='foo')
        self.assertEqual(ably.options.auth_token, 'foo',
                         "Token not set at options")

    def test_with_options_token_callback(self):
        def token_callback(**params):
            return "this_is_not_really_a_token_request"
        AblyRest(options=Options(auth_callback=token_callback))

    def test_with_options_auth_url(self):
        AblyRest(options=Options(auth_url='not_really_an_url'))

    def test_specified_host(self):
        ably = AblyRest(token='foo', options=Options(host="some.other.host"))
        self.assertEqual("some.other.host", ably.options.host,
                         msg="Unexpected host mismatch")

    def test_specified_port(self):
        ably = AblyRest(token='foo', options=Options(port=9998, tls_port=9999))
        self.assertEqual(9999, Defaults.get_port(ably.options),
                         msg="Unexpected port mismatch. Expected: 9999. Actual: %d" %
                         ably.options.tls_port)

    def test_tls_defaults_to_true(self):
        ably = AblyRest(token='foo')
        self.assertTrue(ably.options.tls,
                        msg="Expected encryption to default to true")
        self.assertEqual(Defaults.tls_port, Defaults.get_port(ably.options),
                         msg="Unexpected port mismatch")

    def test_tls_can_be_disabled(self):
        ably = AblyRest(token='foo', options=Options(tls=False))
        self.assertFalse(ably.options.tls,
                         msg="Expected encryption to be False")
        self.assertEqual(Defaults.port, Defaults.get_port(ably.options),
                         msg="Unexpected port mismatch")

    def test_with_no_params(self):
        self.assertRaises(AblyException, AblyRest)

    def test_with_no_auth_params(self):
        self.assertRaises(AblyException, AblyRest, options=Options(port=111))


if __name__ == "__main__":
    unittest.main()
