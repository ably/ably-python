from __future__ import absolute_import

import logging
import unittest
import os 
import sys
import time

from ably import AblyException
from ably import AblyRest
from ably import Auth
from ably import Options
from ably.transport.defaults import Defaults


from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


log = logging.getLogger(__name__)

class TestToken(unittest.TestCase):
    def testClientIdForcesToken(self):
        options =RestSetup.testOptions()
        ablyBasic= AblyRest(options)
        self.assertEqual(ablyBasic.auth.auth_method, Auth.Method.BASIC)
        options.clientId="clientIdForcesToken"
        ablyToken= AblyRest(options)
        self.assertEqual(ablyToken.auth.auth_method, Auth.Method.TOKEN)


    def test_request_token(self):
    	options = RestSetup.testOptions()
    	options.clientId = "clientest_request_token"
        ably = AblyRest(options)
        c1 = ably.channels["test_request_token_channel"]
        c1.publish("msg1", "data")
        history = c1.history()
        current = history.current
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0].data, "data")


    def test_auth_url(self):
        options = RestSetup.testOptions()
        options.authUrl = "http://localhost:8982/get-token"
        ablyWithUrl = AblyRest(options)
        tokenDetails = ablyWithUrl.auth.requestToken()
        self.assertEqual("TokenDetails", tokenDetails.__class__.__name__)


    g_cb_called=False
    def test_auth_callback(self):
        def cb(**kwargs):            
            global g_cb_called
            g_cb_called = True
            return { "token" :"not_a_real_token_request"}
        
        options = RestSetup.testOptions()
        options.auth_callback= cb
        ablyWithUrl = AblyRest(options)
        tokenDetails = ablyWithUrl.auth.requestToken(auth_callback=cb)
        self.assertEqual(ablyWithUrl.auth.auth_method, Auth.Method.TOKEN)
        self.assertEqual("TokenDetails", tokenDetails.__class__.__name__)
        self.assertTrue(g_cb_called)

    def test_token_capability(self):
        options = RestSetup.testOptions()
        options.clientId = "clientIdForcesToken"
        ably = AblyRest(options)
        self.assertEqual(ably.auth.auth_method, Auth.Method.TOKEN)
        c1 = ably.channels["newChannel"]
        self.assertEqual(c1.publish("msg1", "data").error, None)

        restrictedOptions = RestSetup.testOptions(1)
        restrictedOptions.clientId = "clientIdForcesToken2"
        restrictedAbly = AblyRest(restrictedOptions)
        self.assertEqual(restrictedAbly.auth.auth_method, Auth.Method.TOKEN)
        c2 = restrictedAbly.channels["restrictedChannel"]
        response = c2.publish("msg2", "data2")
        self.assertEqual(response.error.statusCode,401)


    def test_expired_token_renews(self):
        options = RestSetup.testOptions()
        options.clientId = "clientIdForcesToken"
        options.ttl =3000
        ably = AblyRest(options)
        
        self.assertEqual(ably.auth.auth_method, Auth.Method.TOKEN)
        c1 = ably.channels["newChannel"]
        self.assertEqual(c1.publish("msg1", "data1").error, None)
        oldToken = ably.auth._token_details.id
        time.sleep(4) #wait for the sleep to stop
        self.assertEqual(c1.publish("msg2", "data2").error, None)
        self.assertFalse(oldToken ==ably.auth._token_details.id, "new token should have been requested")
        

    def test_invalid_token_renews(self):
        options = RestSetup.testOptions()
        options.clientId = "clientIdForcesToken"
        options.ttl =3000
        ably = AblyRest(options)
        
        self.assertEqual(ably.auth.auth_method, Auth.Method.TOKEN)
        c1 = ably.channels["newChannel"]
        self.assertEqual(c1.publish("msg1", "data1").error, None)
        oldToken = ably.auth._token_details.id
        ably.auth._token_details._expires = sys.maxint #prevent this client from automatically noticing the token is expired
        time.sleep(4) #wait for the sleep to stop
        
        response =c1.publish("msg2", "data2")
        self.assertFalse(oldToken ==ably.auth._token_details.id, "new token should have been requested")

    









        





    

