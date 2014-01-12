from __future__ import absolute_import

import unittest

from ably.rest.auth import Auth
from ably.rest.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()

class TestAuth(unittest.TestCase):
    def test_auth_init_key_only(self):
        ably = AblyRest(test_vars["keys"][0]["key_str"])
        self.assertEquals(Auth.Method.BASIC, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_token_only(self):
        options = {
            "auth_token": "this_is_not_really_a_token",
        }

        ably = AblyRest(auth_token="this_is_not_really_a_token")

        self.assertEquals(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        options = {
            "key_id": test_vars["keys"][0]["key_id"],
            "host": test_vars["host"],
            "port": test_vars["port"],
            "tls_port": test_vars["tls_port"],
            "tls": test_vars["encrypted"],
            "auth_callback": token_callback,
        }

        ably = AblyRest(**options)

        try:
            ably.stats(None)
        except:
            pass

        self.assertTrue(callback_called, msg="Token callback not called")
        self.assertEquals(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")
        
    def test_auth_init_with_key_and_client_id(self):
        options = {
            "key": test_vars["keys"][0]["key_str"],
            "client_id": "testClientId",
        }

        ably = AblyRest(**options)

        self.assertEquals(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token(self):
        options = {
            "host": test_vars["host"],
            "port": test_vars["port"],
            "tls_port": test_vars["tls_port"],
            "tls": test_vars["encrypted"],
        }

        ably = AblyRest(**options)

        self.assertEquals(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")
