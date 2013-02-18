from __future__ import absolute_import

import unittest

from ably.auth import Auth
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup


class TestAuth(unittest.TestCase):
    def test_auth_init_key_only(self):
        test_vars = RestSetup.get_test_vars()
        ably = AblyRest(test_vars["keys"][0]["key_str"])
        self.assertEquals(Auth.Method.BASIC, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_token_only(self):
        test_vars = RestSetup.get_test_vars()
        options = {
            "app_id": test_vars["app_id"],
            "auth_token": "this_is_not_really_a_token",
        }

        ably = AblyRest(**options)

        self.assertEquals(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(params):
            callback_called.push(True)
            return "this_is_not_really_a_token_request"

        test_vars = RestSetup.get_test_vars()
        options = {
            "app_id": test_vars["app_id"],
            "rest_host": test_vars["rest_host"],
            "rest_port": test_vars["rest_port"],
            "encrypted": test_vars["encrypted"],
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
        test_vars = RestSetup.get_test_vars()
        options = {
            "key": test_vars["keys"][0]["key_str"],
            "client_id": "testClientId",
        }

        ably = AblyRest(**options)

        self.assertEquals(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token(self):
        # TODO add this test
        pass

