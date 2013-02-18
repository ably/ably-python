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
        key = test_vars['keys'][1]
        token_details = self.ably.auth.request_token(key_id=key['key_id'],
                key_value=key['key_value'])
        self.assertNotNone(token_details.id, msg="Expected token id")
        self.assertEquals(key["capability"], token_details.capability,
                msg="Unexpected capability")

    def test_equal_intersection_with_key(self):
        key = test_vars['keys'][1]
        
        token_params = {
            "capability": key["capability"],
        }

        token_details = self.ably.auth.request_token(key_id=key['key_id'],
                key_value=key['key_value'], 
                token_params=token_params)

        self.assertNotNone(token_details.id, msg="Expected token id")
        self.assertEquals(key["capability"], token_details.capability,
                msg="Unexpected capability")


    def test_empty_ops_intersection(self):
        key = test_vars['keys'][1]
        
        token_params = {
            "capability": json.dumps({
                "testchannel": ["subscribe"],
            }),
        }

        self.assertRaises(AblyException, self.ably.auth.request_token, 
                key_id=key['key_id'],
                key_value=key['key_value'], 
                token_params=token_params)

    def test_empty_paths_intersection(self):
        key = test_vars['keys'][1]
        
        token_params = {
            "capability": json.dumps({
                "testchannelx": ["publish"],
            }),
        }

        self.assertRaises(AblyException, self.ably.auth.request_token, 
                key_id=key['key_id'],
                key_value=key['key_value'], 
                token_params=token_params)

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

