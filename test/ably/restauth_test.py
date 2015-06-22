from __future__ import absolute_import

import logging
import unittest
import os 

from ably import AblyException
from ably import AblyRest
from ably import Auth
from ably import Options
from ably.transport.defaults import Defaults


from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


log = logging.getLogger(__name__)

class TestAuth(unittest.TestCase):
    def test_auth_init_key_only(self):
        
        ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"]))
        log.debug("Method: %s" % ably.auth.auth_method)
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_token_only(self):
        options = {
            "auth_token": "this_is_not_really_a_token",
        }

        ably = AblyRest(Options(auth_token="this_is_not_really_a_token"))

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(**params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        options = RestSetup.testOptions()
        options.auth_callback = token_callback

        ably = AblyRest(options)

        try:
            ably.stats(None)
        except:
            pass

        self.assertTrue(callback_called, msg="Token callback not called")
        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")
        
    def test_auth_init_with_key_and_clientId(self):
        options = Options.with_key(test_vars["keys"][0]["key_str"])
        options.clientId = "testClientId"

        ably = AblyRest(options)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_basic_default(self):
        ably = AblyRest(RestSetup.testOptions())
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_http_basic_throws(self):
        options = Options()
        self.assertEqual(Defaults.get_scheme(options), "https", "https should be default")
        options = Options.with_key(test_vars["keys"][0]["key_str"])   
        options.tls=False
        ably = AblyRest(options)
        channel = ably.channels["newChannel"]
        self.assertFalse(ably.options.tls)
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_method,
            msg="Auth method should be basic")
        
        try:
            with self.assertRaises(AblyException) as cm:
                channel.publish("msg", "data")
        except Exception as e:
            log.debug('test_http_basic_throws: http without tls should throw')
            raise(e)
        
    

