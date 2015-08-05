from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import json
import logging
import time
import unittest

import six
from six.moves import range
import mock

from ably import AblyException
from ably import AblyRest
from ably import Options
from ably.types.message import Message

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

        publish0.publish("publish0", six.u("This is a string message payload"))
        publish0.publish("publish1", b"This is a byte[] message payload")
        publish0.publish("publish2", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish3", ["This is a JSONArray message payload"])

        # Get the history for this channel
        history = publish0.history()
        messages = history.current
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(4, len(messages), msg="Expected 4 messages")

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        self.assertEqual(six.u("This is a string message payload"),
                         message_contents["publish0"],
                         msg="Expect publish0 to be expected String)")
        self.assertEqual(b"This is a byte[] message payload",
                         message_contents["publish1"],
                         msg="Expect publish1 to be expected byte[]. Actual: %s" %
                             str(message_contents['publish1']))
        self.assertEqual({"test": "This is a JSONObject message payload"},
                         message_contents["publish2"],
                         msg="Expect publish2 to be expected JSONObject")
        self.assertEqual(["This is a JSONArray message payload"],
                         message_contents["publish3"],
                         msg="Expect publish3 to be expected JSONObject")

    @unittest.skip("messagepack not implemented")
    def test_publish_various_datatypes_binary(self):
        publish1 = TestRestChannelPublish.ably_binary.channels.publish1

        publish1.publish("publish0", "This is a string message payload")
        publish1.publish("publish1", bytearray("This is a byte[] message payload", "utf_8"))
        publish1.publish("publish2", {"test": "This is a JSONObject message payload"})
        publish1.publish("publish3", ["This is a JSONArray message payload"])

        # Get the history for this channel
        messages = publish1.history()
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(4, len(messages), msg="Expected 4 messages")

        message_contents = dict((m.name, m.data) for m in messages)

        self.assertEqual("This is a string message payload",
                         message_contents["publish0"],
                         msg="Expect publish0 to be expected String)")
        self.assertEqual("This is a byte[] message payload",
                         message_contents["publish1"],
                         msg="Expect publish1 to be expected byte[]")
        self.assertEqual({"test": "This is a JSONObject message payload"},
                         json.loads(message_contents["publish2"]),
                         msg="Expect publish2 to be expected JSONObject")
        self.assertEqual(["This is a JSONArray message payload"],
                         json.loads(message_contents["publish3"]),
                         msg="Expect publish3 to be expected JSONObject")

    def test_publish_message_list(self):
        channel = TestRestChannelPublish.ably.channels["message_list_channel"]
        expected_messages = [Message("name-{}".format(i), str(i)) for i in range(3)]

        channel.publish(messages=expected_messages)

        # Get the history for this channel
        history = channel.history()
        messages = history.current

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), len(expected_messages), msg="Expected 3 messages")

        for m, expected_m in zip(messages, reversed(expected_messages)):
            self.assertEqual(m.name, expected_m.name)
            self.assertEqual(m.data, expected_m.data)

    def test_publish_message_null_name(self):
        channel = TestRestChannelPublish.ably.channels["message_null_name_channel"]

        data = "String message"
        channel.publish(name=None, data=data)

        # Get the history for this channel
        history = channel.history()
        messages = history.current

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), 1, msg="Expected 1 message")

        self.assertIsNone(messages[0].name)
        self.assertEqual(messages[0].data, data)

    def test_publish_message_null_data(self):
        channel = TestRestChannelPublish.ably.channels["message_null_data_channel"]

        name = "Test name"
        channel.publish(name=name, data=None)

        # Get the history for this channel
        history = channel.history()
        messages = history.current

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), 1, msg="Expected 1 message")

        self.assertEqual(messages[0].name, name)
        self.assertIsNone(messages[0].data)

    def test_publish_message_null_name_and_data(self):
        channel = TestRestChannelPublish.ably.channels["null_name_and_data_channel"]

        channel.publish(name=None, data=None)
        channel.publish()

        # Get the history for this channel
        history = channel.history()
        messages = history.current

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), 2, msg="Expected 2 messages")

        for m in messages:
            self.assertIsNone(m.name)
            self.assertIsNone(m.data)

    def test_publish_message_null_name_and_data_keys_arent_sent(self):
        channel = TestRestChannelPublish.ably.channels[
            "null_name_and_data_keys_arent_sent_channel"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish(name=None, data=None)

            history = channel.history()
            messages = history.current

            self.assertIsNotNone(messages, msg="Expected non-None messages")
            self.assertEqual(len(messages), 1, msg="Expected 1 message")

            self.assertEqual(post_mock.call_count, 1)

            posted_body = json.loads(post_mock.call_args[1]['body'])
            self.assertIn('timestamp', posted_body)
            self.assertNotIn('name', posted_body)
            self.assertNotIn('data', posted_body)
