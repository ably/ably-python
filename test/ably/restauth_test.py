from __future__ import absolute_import

import logging
import unittest

from ably import AblyRest
from ably import Auth
from ably import Options


from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


log = logging.getLogger(__name__)


class TestAuth(unittest.TestCase):

    def test_auth_init_key_only(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"])
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_method,
                         msg="Unexpected Auth method mismatch")

    def test_auth_init_token_only(self):
        ably = AblyRest(token="this_is_not_really_a_token")

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                         msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(**params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        options = Options()
        options.key_id = test_vars["keys"][0]["key_id"]
        options.host = test_vars["host"]
        options.port = test_vars["port"]
        options.tls_port = test_vars["tls_port"]
        options.tls = test_vars["tls"]
        options.auth_callback = token_callback

        ably = AblyRest(options=options)

        try:
            ably.stats(None)
        except:
            pass

        self.assertTrue(callback_called, msg="Token callback not called")
        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")
        
    def test_auth_init_with_key_and_client_id(self):
        options = Options(key=test_vars["keys"][0]["key_str"])
        options.client_id = "testClientId"

        ably = AblyRest(options=options)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token(self):
        options = Options(host=test_vars["host"], port=test_vars["port"],
            tls_port=test_vars["tls_port"], tls=test_vars["tls"])

        ably = AblyRest(token="this_is_not_really_a_token",
                        options=options)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")
