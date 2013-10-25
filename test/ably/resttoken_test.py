from __future__ import absolute_import

import time
import json
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestToken(unittest.TestCase):
    def setUp(cls):
        # TODO instantiate a capability correctly
        capability = {"*":["*"]}
        cls.permit_all = json.dumps(capability)
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
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
