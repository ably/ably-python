from __future__ import absolute_import

import time
import unittest

from ably import AblyException
from ably import AblyRest
from ably import Options

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestTime(unittest.TestCase):
    def test_time_accuracy(self):
        ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                restHost=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"]))

        reported_time = ably.time()
        actual_time = time.time() * 1000.0

        self.assertLess(abs(actual_time - reported_time), 2000,
                msg="Time is not within 2 seconds")

    def test_time_without_key_or_token(self):
        ably = AblyRest(RestSetup.testOptions())
        ably.time()
    
    def test_time_fails_without_valid_host(self):
        options = RestSetup.testOptions()
        options.restHost="this.host.does.not.exist",
        ably = AblyRest(options)
        self.assertRaises(AblyException, ably.time)


