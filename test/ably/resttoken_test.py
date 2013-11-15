from __future__ import absolute_import

import time
import json
import unittest

from ably.auth import capability_c14n
from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestToken(unittest.TestCase):
    def setUp(self):
        # TODO instantiate a capability correctly
        capability = {"*":["*"]}
        TestRestToken.permit_all = capability_c14n(capability)
        TestRestToken.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["encrypted"])

    def test_request_token_null_params(self):
        request_time = int(time.time())
        token_details = TestRestToken.ably.auth.request_token()
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertGreaterEqual(request_time - 1, token_details.issued_at,
                msg="Unexpected issued at time")
        self.assertLessEqual(request_time + 1, token_details.issued_at,
                msg="Unexpected issued at time")
        self.assertEquals(TestRestToken.permit_all, token_details.capability,
                msg="Unexpected capability")

    def test_request_token_explicit_timestamp(self):
        request_time = int(time.time())
        token_details = TestRestToken.ably.auth.request_token(timestamp=request_time)
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertGreaterEqual(request_time - 1, token_details.issued_at,
                msg="Unexpected issued at time")
        self.assertLessEqual(request_time + 1, token_details.issued_at,
                msg="Unexpected issued at time")
        self.assertEquals(TestRestToken.permit_all, token_details.capability,
                msg="Unexpected Capability")

    def test_request_token_explicit_invalid_timestamp(self):
        request_time = int(time.time())
        explicit_timestamp = request_time - 30 * 60

        self.assertRaises(AblyException, TestRestToken.ably.auth.request_token,
                timestamp=explicit_timestamp)

    def test_request_token_with_system_timestamp(self):
        request_time = int(time.time())
        token_details = TestRestToken.ably.auth.request_token(query_time=True)
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertGreaterEqual(request_time - 1, token_details.issued_at,
                msg="Unexpected issued at time")
        self.assertLessEqual(request_time + 1, token_details.issued_at,
                msg="Unexpected issued at time")
        self.assertEquals(TestRestToken.permit_all, token_details.capability,
                msg="Unexpected Capability")

    def test_request_token_with_duplicate_nonce(self):
        request_time = int(time.time())
        token_details = TestRestToken.ably.auth.request_token(timestamp=request_time,
                nonce='1234567890123456')
        self.assertIsNotNone(token_details.id, msg="Expected token id")

        self.assertRaises(AblyException, TestRestToken.ably.auth.request_token,
                timestamp=request_time, nonce='1234567890123456')

    def test_request_token_with_capacbility_that_subsets_key_capability(self):
        #TODO: implement this test
        pass

    def test_request_token_with_specified_key(self):
        key = RestSetup.get_test_vars().keys[1]
        token_details = TestRestToken.ably.auth.request_token(key_id=key["key_id"],
                key_value=key["key_value"])
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertEquals(key.capability, token_details.capability,
                msg="Unexpected capability")

    def test_request_token_with_invalid_mac(self):
        self.assertRaises(AblyException, TestRestToken.ably.auth.request_token,
                mac="thisisnotavalidmac")

    def test_request_token_with_specified_ttl(self):
        token_details = TestRestToken.ably.auth.request_token(token_params={ttl:100})
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertEquals(token_details.issued_at + 100,
                token_details.expired, msg="Unexpected expires")

    def test_token_with_excessive_ttl(self):
        excessive_ttl = 365 * 24 * 60 * 60
        self.assertRaises(AblyException, TestRestToken.ably.auth.request_token,
                token_params={"ttl":excessive_ttl})

    def test_token_generation_with_invalid_ttl(self):
        self.assertRaises(AblyException, TestRestToken.ably.auth.request_token,
                token_params={"ttl":-1})
