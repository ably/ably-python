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

class TestToken(unittest.TestCase):
    def testClientIdForcesToken(self):
        options =RestSetup.testOptions()
        ablyBasic= AblyRest(options)
        self.assertEqual(ablyBasic.auth.auth_method, Auth.Method.BASIC)
        options.clientId="clientIdForcesToken"
        ablyToken= AblyRest(options)
        self.assertEqual(ablyToken.auth.auth_method, Auth.Method.TOKEN)


    def testRequestToken(self):
    	options = RestSetup.testOptions()
    	options.clientId = "clientIdForcesToken"
        ably = AblyRest(options)
        c1 = ably.channels["newChannel"]
        c1.publish("msg1", "data")
        history = c1.history()
        current = history.current
        





    

