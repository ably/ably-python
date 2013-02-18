from __future__ import absolute_import

import math
from datetime import time
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestTime(unittest.TestCase):
    def test_time_accuracy(self):
        ably = AblyRest(key=test_vars["key_id"],
                rest_host=test_vars["rest_host"],
                rest_port=test_vars["rest_port"],
                encrypted=test_vars["encrypted"])

        reported_time = ably.time()
        actual_time = time.time() * 1000.0

        self.assertLess(math.abs(actual_time - reported_time), 2000,
                msg("Time is not within 2 seconds"))

    def test_time_without_key_or_token(self):
        ably = AblyRest(app_id=test_vars["app_id"],
                rest_host=test_vars["rest_host"],
                rest_port=test_vars["rest_port"],
                encrypted=test_vars["encrypted"])

        ably.time()
    
    def test_time_fails_without_valid_host(self):
        ably = AblyRest(app_id=test_vars["app_id"],
                rest_host="this.host.does.not.exist",
                rest_port=test_vars["rest_port"])

        self.assertRaises(AblyException, ably.time)


