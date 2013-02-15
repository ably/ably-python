from __future__ import absolute_import

import unittest

from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestInit(unittest.TestCase):
    def test_key_only(self):
        AblyRest(test_vars["keys"][0]["keyStr"])

    def test_key_in_options(self):
        AblyRest(key=test_vars["keys"][0]["keyStr"])

    def test_app_id(self):
        AblyRest(app_id=test_vars["appId"])

    def test_no_credentials(self):
        AblyRest()

    def test_specified_host(self):
        ably = AblyRest(app_id=test_vars["appId"], rest_host="some.other.host")
        self.assertEqual("some.other.host", ably.host_name, 
                msg="Unexpected host mismatch")

    def test_specified_port(self):
        ably = AblyRest(app_id=test_vars["app_id"], rest_port=9999)
        self.assertEqual(9999, ably.rest_port, msg="Unexpected port mismatch")

    def test_encrypted_defaults_to_true(self):
        ably = AblyRest(app_id=test_vars["app_id"])
        self.assertEqual("https", ably.scheme, 
                msg="Unexpected scheme mismatch")

    def test_encryption_can_be_disabled(self):
        ably = AblyRest(app_id=test_vars["app_id"], encrypted=False)
        self.assertEqual("http", ably.scheme,
                msg="Unexpected scheme mismatch")


if __name__ == "__main__":
    unittest.main()

