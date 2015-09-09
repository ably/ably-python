from __future__ import absolute_import

import json
import logging
import unittest

import six
from six.moves import range
import mock
import msgpack

from ably import AblyException
from ably import AblyRest
from ably.types.message import Message

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestRestChannelPublish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"],
                            use_text_protocol=True)

        cls.ably_binary = AblyRest(key=test_vars["keys"][0]["key_str"],
                                   host=test_vars["host"],
                                   port=test_vars["port"],
                                   tls_port=test_vars["tls_port"],
                                   tls=test_vars["tls"],
                                   use_text_protocol=False)

    def test_publish_various_datatypes_text(self):
        publish0 = TestRestChannelPublish.ably.channels["persisted:publish0"]

        publish0.publish("publish0", six.u("This is a string message payload"))
        publish0.publish("publish1", b"This is a byte[] message payload")
        publish0.publish("publish2", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish3", ["This is a JSONArray message payload"])

        # Get the history for this channel
        history = publish0.history()
        messages = history.items
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

    def test_unsuporsed_payload_must_raise_exception(self):
        channel = TestRestChannelPublish.ably.channels["persisted:publish0"]
        for data in [1, 1.1, True]:
            self.assertRaises(AblyException, channel.publish, 'event', data)

    def test_publish_various_datatypes_binary(self):
        publish1 = TestRestChannelPublish.ably_binary.channels.publish1

        publish1.publish("publish0", six.u("This is a string message payload"))
        publish1.publish("publish1", six.b("This is a byte[] message payload"))
        publish1.publish("publish2", {"test": "This is a JSONObject message payload"})
        publish1.publish("publish3", ["This is a JSONArray message payload"])

        # Get the history for this channel
        messages = publish1.history()
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(4, len(messages.items), msg="Expected 3 messages")

        message_contents = dict((m.name, m.data) for m in messages.items)
        self.assertEqual(six.u("This is a string message payload"),
                         message_contents["publish0"],
                         msg="Expect publish0 to be expected String)")
        self.assertEqual(six.b("This is a byte[] message payload"),
                         message_contents["publish1"],
                         msg="Expect publish1 to be expected byte[]")
        self.assertEqual({"test": "This is a JSONObject message payload"},
                         message_contents["publish2"],
                         msg="Expect publish2 to be expected JSONObject")
        self.assertEqual(["This is a JSONArray message payload"],
                         message_contents["publish3"],
                         msg="Expect publish3 to be expected JSONObject")

    def test_publish_message_list(self):
        channel = TestRestChannelPublish.ably.channels["message_list_channel"]
        expected_messages = [Message("name-{}".format(i), str(i)) for i in range(3)]

        channel.publish(messages=expected_messages)

        # Get the history for this channel
        history = channel.history()
        messages = history.items

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), len(expected_messages), msg="Expected 3 messages")

        for m, expected_m in zip(messages, reversed(expected_messages)):
            self.assertEqual(m.name, expected_m.name)
            self.assertEqual(m.data, expected_m.data)

    def test_message_list_generate_one_request_text(self):
        channel = TestRestChannelPublish.ably.channels["message_list_channel_one_request"]
        expected_messages = [Message("name-{}".format(i), six.text_type(i)) for i in range(3)]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish(messages=expected_messages)
        self.assertEqual(post_mock.call_count, 1)
        for i, message in enumerate(json.loads(post_mock.call_args[1]['body'])):
            self.assertEqual(message['name'], 'name-' + str(i))
            self.assertEqual(message['data'], six.text_type(i))

    def test_message_list_generate_one_request_binary(self):
        channel = TestRestChannelPublish.ably_binary.channels["message_list_channel_one_request_bin"]
        expected_messages = [Message("name-{}".format(i), six.text_type(i)) for i in range(3)]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish(messages=expected_messages)
        self.assertEqual(post_mock.call_count, 1)
        for i, message in enumerate(msgpack.unpackb(post_mock.call_args[1]['body'], encoding='utf-8')):
            self.assertEqual(message['name'], 'name-' + str(i))
            self.assertEqual(message['data'], six.text_type(i))

    def test_publish_error(self):
        token_params = {
            "capability": {
                "only_subscribe": ["subscribe"],
            }
        }

        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_text_protocol=True)
        ably.auth.authorise(token_params=token_params)

        with self.assertRaises(AblyException) as cm:
            ably.channels["only_subscribe"].publish()

        self.assertEqual(401, cm.exception.status_code)
        self.assertEqual(40160, cm.exception.code)

    def test_publish_message_null_name(self):
        channel = TestRestChannelPublish.ably.channels["message_null_name_channel"]

        data = "String message"
        channel.publish(name=None, data=data)

        # Get the history for this channel
        history = channel.history()
        messages = history.items

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
        messages = history.items

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
        messages = history.items

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
            messages = history.items

            self.assertIsNotNone(messages, msg="Expected non-None messages")
            self.assertEqual(len(messages), 1, msg="Expected 1 message")

            self.assertEqual(post_mock.call_count, 1)

            posted_body = json.loads(post_mock.call_args[1]['body'])
            self.assertIn('timestamp', posted_body)
            self.assertNotIn('name', posted_body)
            self.assertNotIn('data', posted_body)

    def test_message_attr(self):
        publish0 = TestRestChannelPublish.ably.channels["persisted:publish-message_attr"]
        messages = [Message('publish',
                            {"test": "This is a JSONObject message payload"},
                            client_id='client_id')]
        publish0.publish("publish", messages=messages)

        # Get the history for this channel
        history = publish0.history()
        message = history.items[0]
        self.assertIsInstance(message, Message)
        self.assertTrue(message.id)
        self.assertTrue(message.name)
        self.assertEqual(message.data,
                         {six.u('test'): six.u('This is a JSONObject message payload')})
        self.assertEqual(message.encoding, '')
        self.assertEqual(message.client_id, 'client_id')
        self.assertIsInstance(message.timestamp, int)
