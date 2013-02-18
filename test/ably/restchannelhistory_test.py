from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestChannelHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                rest_host=test_vars["rest_host"],
                rest_port=test_vars["rest_port"],
                encrypted=test_vars["encrypted"])

    @property
    def ably(self):
        return TestRestChannelHistory.ably

    def test_publish_events_various_datatypes(self):
        pass
