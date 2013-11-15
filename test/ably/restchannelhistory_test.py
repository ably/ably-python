from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestChannelHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["encrypted"])
        cls.time_offset = cls.ably.time() - int(time.time())

    @property
    def ably(self):
        return TestRestChannelHistory.ably

    def test_publish_events_various_datatypes(self):
        history0 = TestRestChannelHistory.ably.channels.get('persisted:channelhistory_types')
        history0.publish('history0', True)
        history0.publish('history1', 24)
        history0.publish('history2', 24.234)
        history0.publish('history3', 'This is a string message')
        history0.publish('history4', bytearray('This is a byte[] message', 'utf8'))
        history0.publish('history5', {'test': 'This is a JSONObject message payload'})
        history0.publish('history6', ['This is a JSONArray message payload'])

        # Wait for the history to be persisted
        time.sleep(16)

        messages = history0.history()

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEquals(7, len(messages), msg="Expected 7 messages")
        
        message_contents = dict((m.name, m.data) for m in messages)

        self.assertEquals(True, message_contents["publish0"],
                msg="Expect publish0 to be Boolean(true)")
        self.assertEquals(24, int(message_contents["publish1"]),
                msg="Expect publish1 to be Int(24)")
        self.assertEquals(24.234, float(message_contents["publish2"]),
                msg="Expect publish2 to be Double(24.234)")
        self.assertEquals("This is a string message payload",
                message_contents["publish3"],
                msg="Expect publish3 to be expected String)")
        self.assertEquals("This is a byte[] message payload",
                message_contents["publish4"],
                msg="Expect publish4 to be expected byte[]")
        self.assertEquals({"test": "This is a JSONObject message payload"},
                json.loads(message_contents["publish5"]),
                msg="Expect publish5 to be expected JSONObject")
        self.assertEquals(["This is a JSONArray message payload"],
                json.loads(message_contents["publish6"]),
                msg="Expect publish6 to be expected JSONObject")
