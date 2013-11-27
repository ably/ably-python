from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import logging
import time
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


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
        history0.publish('history3', 'This is a string message payload')
        history0.publish('history4', bytearray('This is a byte[] message', 'utf8'))
        history0.publish('history5', {'test': 'This is a JSONObject message payload'})
        history0.publish('history6', ['This is a JSONArray message payload'])

        # Wait for the history to be persisted
        time.sleep(16)

        messages = history0.history()

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEquals(7, len(messages), msg="Expected 7 messages")
        
        log.debug(messages)
        message_contents = {m.name:m.data for m in messages}
        log.debug(message_contents)

        self.assertEquals(True, message_contents["history0"],
                msg="Expect history0 to be Boolean(true)")
        self.assertEquals(24, int(message_contents["history1"]),
                msg="Expect history1 to be Int(24)")
        self.assertEquals(24.234, float(message_contents["history2"]),
                msg="Expect history2 to be Double(24.234)")
        self.assertEquals("This is a string message payload",
                message_contents["history3"],
                msg="Expect history3 to be expected String)")
        self.assertEquals("This is a byte[] message payload",
                message_contents["history4"],
                msg="Expect history4 to be expected byte[]")
        self.assertEquals({"test": "This is a JSONObject message payload"},
                json.loads(message_contents["history5"]),
                msg="Expect history5 to be expected JSONObject")
        self.assertEquals(["This is a JSONArray message payload"],
                json.loads(message_contents["history6"]),
                msg="Expect history6 to be expected JSONObject")
