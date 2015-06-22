from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import json
import logging
import sys
import time
import unittest

import six

from ably import AblyException
from ably import AblyRest
from ably import Options
from ably import ChannelOptions
from ably.types.presencemessage import PresenceMessage
from ably.types.presencemessage import PresenceAction
from ably.types.searchparams import SearchParams

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)
logging.StreamHandler(sys.stdout)

class TestRestPresence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"],
                use_text_protocol=True))

    def test_presence_simple(self):
        channelName = "persisted:presence_fixtures"
        channel1 = TestRestPresence.ably.channels.get(channelName)
        presence = channel1.presence()
        result = presence.get()
        self.assertTrue(result.has_first)
        current = result.current
        self.assertTrue(current)
        self.assertEqual(6, len(current), msg="Expected 6 presence messages")
        p = current[0]
        self.assertEqual(p.action, PresenceAction.LEAVE)
        self.assertEqual(p.clientId, "client_bool")
        self.assertEqual(p.client_data, "true")

    def test_presence_clientId(self):
        channelName = "persisted:presence_fixtures"
        channel1 = TestRestPresence.ably.channels.get(channelName)
        result = channel1.presence().get(SearchParams(clientId="client_string"))
        self.assertTrue(result.has_first)
        current = result.current
        self.assertTrue(current)
        print("TODO this fails. clientId filter does nothing: " + str(len(current)))
        self.assertEqual(1, len(current), msg="Expected 1 presence message")

        p = current[0]
        self.assertEqual(p.action, PresenceAction.LEAVE)
        self.assertEqual(p.clientId, "client_string")
        self.assertEqual(p.client_data, "This is a string clientData payload")

    def test_presence_connection_id(self):
        print("TODO implement")

    def test_presence_over_1000(self):
        channel1 = TestRestPresence.ably.channels.get("channelName")
        try:
            with self.assertRaises(AblyException) as cm:
                result = channel1.presence().get(SearchParams(limit=1001))
        except Exception as e:
            log.debug('test_presence_over_1000: presence limit over 1000 not raising exception')
            raise(e)

    def test_presence_history_simple(self):
        channelName = "persisted:presence_fixtures"
        channel1 = TestRestPresence.ably.channels.get(channelName)
        result = channel1.presence().history()
        self.assertTrue(result.has_first)
        current = result.items
        self.assertTrue(current)
        self.assertEqual(6, len(current), msg="Expected 6 presence messages")
        p = current[0]
        self.assertEqual(p.action, PresenceAction.UPDATE)
        self.assertEqual(p.clientId, "client_encoded")
        self.assertEqual(p.client_data, "HO4cYSP8LybPYBPZPHQOtuD53yrD3YV3NBoTEYBh4U0N1QXHbtkfsDfTspKeLQFt")

    def test_presence_history_forwards(self):
        channelName = "persisted:presence_fixtures"
        channel1 = TestRestPresence.ably.channels.get(channelName)
        result = channel1.presence().history(SearchParams(backwards=False))
        self.assertTrue(result.has_first)
        current = result.items
        self.assertTrue(current)
        self.assertEqual(6, len(current), msg="Expected 6 presence messages")
        p = current[0]
        self.assertEqual(p.action, PresenceAction.UPDATE)
        self.assertEqual(p.clientId, "client_bool")
        self.assertEqual(p.client_data, "true")





