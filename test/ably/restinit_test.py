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
        AblyRest(Options.with_key(test_vars["keys"][0]["key_str"]))

    def test_key_in_options(self):
        AblyRest(Options.with_key(test_vars["keys"][0]["key_str"]))

    def test_specified_host(self):
        ably = AblyRest(Options(host="some.other.host"))
        self.assertEqual("some.other.host", ably.options.host, 
                msg="Unexpected host mismatch")

    def test_specified_port(self):
        ably = AblyRest(Options(port=9998, tls_port=9999))
        self.assertEqual(9999, Defaults.get_port(ably.options),
                msg="Unexpected port mismatch. Expected: 9999. Actual: %d" % ably.options.tls_port)

    def test_tls_defaults_to_true(self):
        ably = AblyRest()
        self.assertTrue(ably.options.tls,
                msg="Expected encryption to default to true")
        self.assertEqual(Defaults.tls_port, Defaults.get_port(ably.options),
                msg="Unexpected port mismatch")

    def test_tls_can_be_disabled(self):
        ably = AblyRest(Options(tls=False))
        self.assertFalse(ably.options.tls,
                msg="Expected encryption to be False")
        self.assertEqual(Defaults.port, Defaults.get_port(ably.options),
                msg="Unexpected port mismatch")


if __name__ == "__main__":
    unittest.main()

