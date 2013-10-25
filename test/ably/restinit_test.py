from __future__ import absolute_import

import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestInit(unittest.TestCase):
    def test_key_only(self):
        AblyRest(test_vars["keys"][0]["key_str"])

    def test_key_in_options(self):
        AblyRest(key=test_vars["keys"][0]["key_str"])

    def test_no_credentials(self):
        self.assertRaises(AblyException, AblyRest)

    def test_specified_host(self):
        ably = AblyRest(host="some.other.host")
        self.assertEqual("some.other.host", ably.host, 
                msg="Unexpected host mismatch")

    def test_specified_port(self):
        ably = AblyRest(port=9998, tls_port=9999)
        self.assertEqual(9998, ably.__port, msg="Unexpected port mismatch")
        self.assertEqual(9999, ably.__tls_port, msg="Unexpected port mismatch")

    def test_encrypted_defaults_to_true(self):
        ably = AblyRest()
        self.assertEqual("https", ably.scheme, 
                msg="Unexpected scheme mismatch")
        self.assertTrue(ably.tls, msg="Expected encryption to default to true")

    def test_encryption_can_be_disabled(self):
        ably = AblyRest(tls=False)
        self.assertEqual("http", ably.scheme,
                msg="Unexpected scheme mismatch")
        self.assertFalse(ably.tls, msg="Expected encryption to be False")


if __name__ == "__main__":
    unittest.main()

