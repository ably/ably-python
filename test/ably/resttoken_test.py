from __future__ import absolute_import

import time
import json
import logging
import unittest

from ably import AblyException
from ably import AblyRest
from ably import Capability
from ably import Options

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestRestToken(unittest.TestCase):
    def server_time(self):
        return int(self.ably.time() / 1000.0)

    def setUp(self):
        capability = {"*":["*"]}
        self.permit_all = unicode(Capability(capability))
        self.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"]))

    def test_request_token_null_params(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token()
        post_time = self.server_time()
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertGreaterEqual(token_details.issued_at,
                pre_time,
                msg="Unexpected issued at time")
        self.assertLessEqual(token_details.issued_at,
                post_time,
                msg="Unexpected issued at time")
        self.assertEquals(self.permit_all,
                unicode(token_details.capability),
                msg="Unexpected capability")

    def test_request_token_explicit_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(token_params={
            "timestamp":pre_time
            })
        post_time = self.server_time()
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertGreaterEqual(token_details.issued_at,
                pre_time,
                msg="Unexpected issued at time")
        self.assertLessEqual(token_details.issued_at,
                post_time,
                msg="Unexpected issued at time")
        self.assertEquals(self.permit_all,
                unicode(Capability(token_details.capability)),
                msg="Unexpected Capability")

    def test_request_token_explicit_invalid_timestamp(self):
        request_time = self.server_time()
        explicit_timestamp = request_time - 30 * 60

        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"timestamp":explicit_timestamp})

    def test_request_token_with_system_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(query_time=True)
        post_time = self.server_time()
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertGreaterEqual(token_details.issued_at,
                pre_time,
                msg="Unexpected issued at time")
        self.assertLessEqual(token_details.issued_at,
                post_time,
                msg="Unexpected issued at time")
        self.assertEquals(self.permit_all,
                unicode(Capability(token_details.capability)),
                msg="Unexpected Capability")

    def test_request_token_with_duplicate_nonce(self):
        request_time = self.server_time()
        token_details = self.ably.auth.request_token(token_params={
            "timestamp":request_time,
            "nonce":'1234567890123456'
        })
        self.assertIsNotNone(token_details.id, msg="Expected token id")

        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={
                    "timestamp":request_time,
                    "nonce":'1234567890123456'
                })

    def test_request_token_with_capacbility_that_subsets_key_capability(self):
        #TODO: implement this test
        pass

    def test_request_token_with_specified_key(self):
        key = RestSetup.get_test_vars()["keys"][1]
        token_details = self.ably.auth.request_token(key_id=key["key_id"],
                key_value=key["key_value"])
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertEquals(key.get("capability"),
                token_details.capability,
                msg="Unexpected capability")

    def test_request_token_with_invalid_mac(self):
        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"mac":"thisisnotavalidmac"})

    def test_request_token_with_specified_ttl(self):
        token_details = self.ably.auth.request_token(token_params={
            "ttl":100
        })
        self.assertIsNotNone(token_details.id, msg="Expected token id")
        self.assertEquals(token_details.issued_at + 100,
                token_details.expires, msg="Unexpected expires")

    def test_token_with_excessive_ttl(self):
        excessive_ttl = 365 * 24 * 60 * 60
        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"ttl":excessive_ttl})

    def test_token_generation_with_invalid_ttl(self):
        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"ttl":-1})
