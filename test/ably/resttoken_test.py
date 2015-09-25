from __future__ import absolute_import

import time
import json
import logging
import unittest

from mock import patch
import six

from ably import AblyException
from ably import AblyRest
from ably import Capability
from ably import Options

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestToken(unittest.TestCase):
    def server_time(self):
        return self.ably.time()

    def setUp(self):
        capability = {"*":["*"]}
        self.permit_all = six.text_type(Capability(capability))
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_request_token_null_params(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token()
        post_time = self.server_time()
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertGreaterEqual(token_details.issued,
                pre_time,
                msg="Unexpected issued time")
        self.assertLessEqual(token_details.issued,
                post_time,
                msg="Unexpected issued time")
        self.assertEqual(self.permit_all,
                six.text_type(token_details.capability),
                msg="Unexpected capability")

    def test_request_token_explicit_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(token_params={
            "timestamp":pre_time
            })
        post_time = self.server_time()
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertGreaterEqual(token_details.issued,
                pre_time,
                msg="Unexpected issued time")
        self.assertLessEqual(token_details.issued,
                post_time,
                msg="Unexpected issued time")
        self.assertEqual(self.permit_all,
                six.text_type(Capability(token_details.capability)),
                msg="Unexpected Capability")

    def test_request_token_explicit_invalid_timestamp(self):
        request_time = self.server_time()
        explicit_timestamp = request_time - 30 * 60 * 1000

        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"timestamp":explicit_timestamp})

    def test_request_token_with_system_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(query_time=True)
        post_time = self.server_time()
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertGreaterEqual(token_details.issued,
                pre_time,
                msg="Unexpected issued time")
        self.assertLessEqual(token_details.issued,
                post_time,
                msg="Unexpected issued time")
        self.assertEqual(self.permit_all,
                six.text_type(Capability(token_details.capability)),
                msg="Unexpected Capability")

    def test_request_token_with_duplicate_nonce(self):
        request_time = self.server_time()
        token_details = self.ably.auth.request_token(token_params={
            "timestamp":request_time,
            "nonce":'1234567890123456'
        })
        self.assertIsNotNone(token_details.token, msg="Expected token")

        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={
                    "timestamp":request_time,
                    "nonce":'1234567890123456'
                })

    def test_request_token_with_capability_that_subsets_key_capability(self):
        capability = Capability({
            "onlythischannel": ["subscribe"]
        })

        token_params = {
            "capability": capability,
        }

        token_details = self.ably.auth.request_token(token_params=token_params)

        self.assertIsNotNone(token_details)
        self.assertIsNotNone(token_details.token)
        self.assertEqual(capability, token_details.capability,
                msg="Unexpected capability")

    def test_request_token_with_specified_key(self):
        key = RestSetup.get_test_vars()["keys"][1]
        token_details = self.ably.auth.request_token(key_name=key["key_name"],
                key_secret=key["key_secret"])
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertEqual(key.get("capability"),
                token_details.capability,
                msg="Unexpected capability")

    @dont_vary_protocol
    def test_request_token_with_invalid_mac(self):
        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"mac":"thisisnotavalidmac"})

    def test_request_token_with_specified_ttl(self):
        token_details = self.ably.auth.request_token(token_params={
            "ttl":100
        })
        self.assertIsNotNone(token_details.token, msg="Expected token")
        self.assertEqual(token_details.issued + 100,
                token_details.expires, msg="Unexpected expires")

    @dont_vary_protocol
    def test_token_with_excessive_ttl(self):
        excessive_ttl = 365 * 24 * 60 * 60 * 1000
        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"ttl":excessive_ttl})

    @dont_vary_protocol
    def test_token_generation_with_invalid_ttl(self):
        self.assertRaises(AblyException, self.ably.auth.request_token,
                token_params={"ttl":-1})

    def test_token_generation_with_local_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.request_token()
            self.assertTrue(local_time.called)
            self.assertFalse(server_time.called)

    def test_token_generation_with_server_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.request_token(query_time=True)
            self.assertFalse(local_time.called)
            self.assertTrue(server_time.called)
