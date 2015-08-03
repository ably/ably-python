from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import json
import logging
import time
import unittest

import six

from ably import AblyException
from ably import AblyRest
from ably import Options

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)

class TestRestChannelPublish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"],
                use_text_protocol=True))

        cls.ably_binary = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"],
                use_text_protocol=False))

    def test_publish_various_datatypes_text(self):
        publish0 = TestRestChannelPublish.ably.channels["persisted:publish0"]

        publish0.publish("publish0", True)
        publish0.publish("publish1", 24)
        publish0.publish("publish2", 24.234)
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", b"This is a byte[] message payload")
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        # Get the history for this channel
        history = publish0.history()
        messages = history.current
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(7, len(messages), msg="Expected 7 messages")
        
        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        self.assertEqual(True, message_contents["publish0"],
                msg="Expect publish0 to be Boolean(true)")
        self.assertEqual(24, int(message_contents["publish1"]),
                msg="Expect publish1 to be Int(24)")
        self.assertEqual(24.234, float(message_contents["publish2"]),
                msg="Expect publish2 to be Double(24.234)")
        self.assertEqual(six.u("This is a string message payload"),
                message_contents["publish3"],
                msg="Expect publish3 to be expected String)")
        self.assertEqual(b"This is a byte[] message payload",
                message_contents["publish4"],
                msg="Expect publish4 to be expected byte[]. Actual: %s" % str(message_contents['publish4']))
        self.assertEqual({"test": "This is a JSONObject message payload"},
                message_contents["publish5"],
                msg="Expect publish5 to be expected JSONObject")
        self.assertEqual(["This is a JSONArray message payload"],
                message_contents["publish6"],
                msg="Expect publish6 to be expected JSONObject")

    def test_publish_various_datatypes_binary(self):
        publish1 = TestRestChannelPublish.ably_binary.channels.publish1

        publish1.publish("publish0", True)
        publish1.publish("publish1", 24)
        publish1.publish("publish2", 24.234)
        publish1.publish("publish3", "This is a string message payload")
        publish1.publish("publish4", bytearray("This is a byte[] message payload", "utf_8"))
        publish1.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish1.publish("publish6", ["This is a JSONArray message payload"])

        # Get the history for this channel
        messages = publish1.history()
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(7, len(messages), msg="Expected 7 messages")

        message_contents = dict((m.name, m.data) for m in messages)

        self.assertEqual(True, message_contents["publish0"],
               msg="Expect publish0 to be Boolean(true)")
        self.assertEqual(24, int(message_contents["publish1"]),
               msg="Expect publish1 to be Int(24)")
        self.assertEqual(24.234, float(message_contents["publish2"]),
               msg="Expect publish2 to be Double(24.234)")
        self.assertEqual("This is a string message payload",
               message_contents["publish3"],
               msg="Expect publish3 to be expected String)")
        self.assertEqual("This is a byte[] message payload",
               message_contents["publish4"],
               msg="Expect publish4 to be expected byte[]")
        self.assertEqual({"test": "This is a JSONObject message payload"},
               json.loads(message_contents["publish5"]),
               msg="Expect publish5 to be expected JSONObject")
        self.assertEqual(["This is a JSONArray message payload"],
               json.loads(message_contents["publish6"]),
               msg="Expect publish6 to be expected JSONObject")

