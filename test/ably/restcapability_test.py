from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestCapability(unittest.TestCase):
    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                rest_host=test_vars["rest_host"],
                rest_port=test_vars["rest_port"],
                encrypted=test_vars["encrypted"])

    def test_blanket_intersection_with_key(self):
        pass

    def test_equal_intersection_with_key(self):
        pass

    def test_empty_ops_intersection(self):
        pass

    def test_empty_paths_intersection(self):
        pass

    def test_non_empty_ops_intersection(self):
        pass

    def test_non_empty_paths_intersection(self):
        pass

    def test_wildcard_ops_intersection(self):
        pass

    def test_wildcard_ops_intersection_2(self):
        pass

    def test_wildcard_resources_intersection(self):
        pass

    def test_wildcard_resources_intersection_2(self):
        pass

    def test_wildcard_resources_intersection_3(self):
        pass

    def test_invalid_capabilities(self):
        pass

    def test_invalid_capabilities_2(self):
        pass

    def test_invalid_capabilities_3(self):
        pass

