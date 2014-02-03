from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import json
import unittest

from ably import AblyRest
from ably import Options
from ably.types.capability import Capability
from ably.util.exceptions import AblyException

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()

class TestRestCapability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"]))

    @property
    def ably(self):
        return self.__class__.ably

    def test_blanket_intersection_with_key(self):
        key = test_vars['keys'][1]
        token_details = self.ably.auth.request_token(key_id=key['key_id'],
                key_value=key['key_value'])
        self.assertIsNotNone(token_details["id"], msg="Expected token id")
        self.assertEquals(key["capability"],
                unicode(Capability(token_details["capability"])),
                msg="Unexpected capability.")

    def test_equal_intersection_with_key(self):
        key = test_vars['keys'][1]
        
        token_params = {
            "capability": key["capability"],
        }

        token_details = self.ably.auth.request_token(key_id=key['key_id'],
                key_value=key['key_value'], 
                token_params=token_params)

        self.assertIsNotNone(token_details["id"], msg="Expected token id")
        self.assertEquals(key["capability"],
                unicode(Capability(token_details["capability"])),
                msg="Unexpected capability")


    def test_empty_ops_intersection(self):
        key = test_vars['keys'][1]
        
        token_params = {
            "capability": {
                "testchannel": ["subscribe"],
            },
        }

        self.assertRaises(AblyException, self.ably.auth.request_token, 
                key_id=key['key_id'],
                key_value=key['key_value'], 
                token_params=token_params)

    def test_empty_paths_intersection(self):
        key = test_vars['keys'][1]
        
        token_params = {
            "capability": {
                "testchannelx": ["publish"],
            },
        }

        self.assertRaises(AblyException, self.ably.auth.request_token, 
                key_id=key['key_id'],
                key_value=key['key_value'], 
                token_params=token_params)

    def test_non_empty_ops_intersection(self):
        key = test_vars['keys'][4]
        
        kwargs = {
            "key_id": key["key_id"],
            "key_value": key["key_value"],
            "token_params": {
                "capability": {
                    "channel2": ["presence", "subscribe"],
                },
            },
        }

        expected_capability = unicode(Capability({
            "channel2": ["subscribe"]
        }))

        token_details = self.ably.auth.request_token(**kwargs)

        self.assertIsNotNone(token_details["id"], msg="Expected token id")
        self.assertEquals(expected_capability,
                unicode(Capability(token_details["capability"])),
                msg="Unexpected capability")

    def test_non_empty_paths_intersection(self):
        key = test_vars['keys'][4]
        
        kwargs = {
            "key_id": key["key_id"],
            "key_value": key["key_value"],
            "token_params": {
                "capability": {
                    "channel2": ["presence", "subscribe"],
                    "channelx": ["presence", "subscribe"],
                },
            },
        }

        expected_capability = unicode(Capability({
            "channel2": ["subscribe"]
        }))

        token_details = self.ably.auth.request_token(**kwargs)

        self.assertIsNotNone(token_details["id"], msg="Expected token id")
        self.assertEquals(expected_capability,
                unicode(Capability({"channel2":["subscribe"]})),
                msg="Unexpected capability")

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

