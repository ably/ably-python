from __future__ import absolute_import

import binascii
import json
import logging
import os
import uuid

import six
from six.moves import range
import mock
import msgpack
import requests

from ably import AblyException, IncompatibleClientIdException
from ably import AblyRest
from ably.rest.auth import Auth
from ably.types.message import Message
from ably.types.tokendetails import TokenDetails

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestChannelPublish(BaseTestCase):
    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])
        self.client_id = uuid.uuid4().hex
        self.ably_with_client_id = AblyRest(key=test_vars["keys"][0]["key_str"],
                                            rest_host=test_vars["host"],
                                            port=test_vars["port"],
                                            tls_port=test_vars["tls_port"],
                                            tls=test_vars["tls"],
                                            client_id=self.client_id)

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.ably_with_client_id.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_publish_various_datatypes_text(self):
        publish0 = self.ably.channels[
            self.protocol_channel_name('persisted:publish0')]

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

    @dont_vary_protocol
    def test_unsuporsed_payload_must_raise_exception(self):
        channel = self.ably.channels["persisted:publish0"]
        for data in [1, 1.1, True]:
            self.assertRaises(AblyException, channel.publish, 'event', data)

    def test_publish_message_list(self):
        channel = self.ably.channels[
            self.protocol_channel_name('persisted:message_list_channel')]

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

    def test_message_list_generate_one_request(self):
        channel = self.ably.channels[
            self.protocol_channel_name('persisted:message_list_channel_one_request')]

        expected_messages = [Message("name-{}".format(i), six.text_type(i)) for i in range(3)]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish(messages=expected_messages)
        self.assertEqual(post_mock.call_count, 1)

        if self.use_binary_protocol:
            messages = msgpack.unpackb(post_mock.call_args[1]['body'], encoding='utf-8')
        else:
            messages = json.loads(post_mock.call_args[1]['body'])

        for i, message in enumerate(messages):
            self.assertEqual(message['name'], 'name-' + str(i))
            self.assertEqual(message['data'], six.text_type(i))

    def test_publish_error(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_binary_protocol=self.use_binary_protocol)
        ably.auth.authorize(
            token_params={'capability': {"only_subscribe": ["subscribe"]}})

        with self.assertRaises(AblyException) as cm:
            ably.channels["only_subscribe"].publish()

        self.assertEqual(401, cm.exception.status_code)
        self.assertEqual(40160, cm.exception.code)

    def test_publish_message_null_name(self):
        channel = self.ably.channels[
            self.protocol_channel_name('persisted:message_null_name_channel')]

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
        channel = self.ably.channels[
            self.protocol_channel_name('persisted:message_null_data_channel')]

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
        channel = self.ably.channels[
            self.protocol_channel_name('persisted:null_name_and_data_channel')]

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
        channel = self.ably.channels[
            self.protocol_channel_name('persisted:null_name_and_data_keys_arent_sent_channel')]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish(name=None, data=None)

            history = channel.history()
            messages = history.items

            self.assertIsNotNone(messages, msg="Expected non-None messages")
            self.assertEqual(len(messages), 1, msg="Expected 1 message")

            self.assertEqual(post_mock.call_count, 1)

            if self.use_binary_protocol:
                posted_body = msgpack.unpackb(post_mock.call_args[1]['body'], encoding='utf-8')
            else:
                posted_body = json.loads(post_mock.call_args[1]['body'])

            self.assertIn('timestamp', posted_body)
            self.assertNotIn('name', posted_body)
            self.assertNotIn('data', posted_body)

    def test_message_attr(self):
        publish0 = self.ably.channels[
            self.protocol_channel_name('persisted:publish_message_attr')]

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

    def test_token_is_bound_to_options_client_id_after_publish(self):
        # null before publish
        self.assertIsNone(self.ably_with_client_id.auth.token_details)

        # created after message publish and will have client_id
        channel = self.ably_with_client_id.channels[
            self.protocol_channel_name('persisted:restricted_to_client_id')]
        channel.publish(name='publish', data='test')

        # defined after publish
        self.assertIsInstance(self.ably_with_client_id.auth.token_details, TokenDetails)
        self.assertEqual(self.ably_with_client_id.auth.token_details.client_id, self.client_id)
        self.assertEqual(self.ably_with_client_id.auth.auth_mechanism, Auth.Method.TOKEN)
        self.assertEqual(channel.history().items[0].client_id, self.client_id)

    def test_publish_message_without_client_id_on_identified_client(self):
        channel = self.ably_with_client_id.channels[
            self.protocol_channel_name('persisted:no_client_id_identified_client')]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish(name='publish', data='test')

            history = channel.history()
            messages = history.items

            self.assertIsNotNone(messages, msg="Expected non-None messages")
            self.assertEqual(len(messages), 1, msg="Expected 1 message")

            self.assertEqual(post_mock.call_count, 2)

            if self.use_binary_protocol:
                posted_body = msgpack.unpackb(
                    post_mock.mock_calls[0][2]['body'], encoding='utf-8')
            else:
                posted_body = json.loads(
                    post_mock.mock_calls[0][2]['body'])

            self.assertNotIn('client_id', posted_body)

            # Get the history for this channel
            history = channel.history()
            messages = history.items

            self.assertIsNotNone(messages, msg="Expected non-None messages")
            self.assertEqual(len(messages), 1, msg="Expected 1 message")

            self.assertEqual(messages[0].client_id, self.ably_with_client_id.client_id)

    def test_publish_message_with_client_id_on_identified_client(self):
        # works if same
        channel = self.ably_with_client_id.channels[
            self.protocol_channel_name('persisted:with_client_id_identified_client')]
        channel.publish(name='publish', data='test',
                        client_id=self.ably_with_client_id.client_id)

        history = channel.history()
        messages = history.items

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), 1, msg="Expected 1 message")

        self.assertEqual(messages[0].client_id, self.ably_with_client_id.client_id)

        # fails if different
        with self.assertRaises(IncompatibleClientIdException):
            channel.publish(name='publish', data='test',
                            client_id='invalid')

    def test_publish_message_with_wrong_client_id_on_implicit_identified_client(self):
        new_token = self.ably.auth.authorize(
            token_params={'client_id': uuid.uuid4().hex})
        new_ably = AblyRest(token=new_token.token,
                            rest_host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"],
                            use_binary_protocol=self.use_binary_protocol)
        channel = new_ably.channels[
            self.protocol_channel_name('persisted:wrong_client_id_implicit_client')]

        with self.assertRaises(AblyException) as cm:
            channel.publish(name='publish', data='test',
                            client_id='invalid')

        the_exception = cm.exception
        self.assertEqual(400, the_exception.status_code)
        self.assertEqual(40012, the_exception.code)

    # RSA15b
    def test_wildcard_client_id_can_publish_as_others(self):
        wildcard_token_details = self.ably.auth.request_token({'client_id': '*'})
        wildcard_ably = AblyRest(token_details=wildcard_token_details,
                                 rest_host=test_vars["host"],
                                 port=test_vars["port"],
                                 tls_port=test_vars["tls_port"],
                                 tls=test_vars["tls"],
                                 use_binary_protocol=self.use_binary_protocol)

        self.assertEqual(wildcard_ably.auth.client_id, '*')
        channel = wildcard_ably.channels[
            self.protocol_channel_name('persisted:wildcard_client_id')]
        channel.publish(name='publish1', data='no client_id')
        some_client_id = uuid.uuid4().hex
        channel.publish(name='publish2', data='some client_id',
                        client_id=some_client_id)

        history = channel.history()
        messages = history.items

        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(len(messages), 2, msg="Expected 2 messages")

        self.assertEqual(messages[0].client_id, some_client_id)
        self.assertIsNone(messages[1].client_id)

    # TM2h
    @dont_vary_protocol
    def test_invalid_connection_key(self):
        channel = self.ably.channels["persisted:invalid_connection_key"]
        message = Message(data='payload', connection_key='should.be.wrong')
        with self.assertRaises(AblyException) as cm:
            channel.publish(messages=[message])

        self.assertEqual(400, cm.exception.status_code)
        self.assertEqual(40006, cm.exception.code)

    # TM2i, RSL6a2, RSL1h
    def test_publish_extras(self):
        channel = self.ably.channels[
            self.protocol_channel_name('canpublish:extras_channel')]
        extras = {
            'push': {
                'notification': {"title": "Testing"},
            }
        }
        channel.publish(name='test-name', data='test-data', extras=extras)

        # Get the history for this channel
        history = channel.history()
        message = history.items[0]
        self.assertEqual(message.name, 'test-name')
        self.assertEqual(message.data, 'test-data')
        self.assertEqual(message.extras, extras)

    # RSL6a1
    def test_interoperability(self):
        name = self.protocol_channel_name('persisted:interoperability_channel')
        channel = self.ably.channels[name]

        url = 'https://%s/channels/%s/messages' % (test_vars["host"], name)
        key = test_vars['keys'][0]
        auth = (key['key_name'], key['key_secret'])

        type_mapping = {
            'string': six.text_type,
            'jsonObject': dict,
            'jsonArray': list,
            'binary': bytearray,
        }

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(root_dir, 'submodules', 'test-resources', 'messages-encoding.json')
        with open(path) as f:
            data = json.load(f)
            for input_msg in data['messages']:
                data = input_msg['data']
                encoding = input_msg['encoding']
                expected_type = input_msg['expectedType']
                if expected_type == 'binary':
                    expected_value = input_msg.get('expectedHexValue')
                    expected_value = expected_value.encode('ascii')
                    expected_value = binascii.a2b_hex(expected_value)
                else:
                    expected_value = input_msg.get('expectedValue')

                # 1)
                channel.publish(data=expected_value)
                r = requests.get(url, auth=auth)
                item = r.json()[0]
                self.assertEqual(item.get('encoding'), encoding)
                if encoding == 'json':
                    self.assertEqual(
                        json.loads(item['data']),
                        json.loads(data),
                    )
                else:
                    self.assertEqual(item['data'], data)

                # 2)
                channel.publish(messages=[Message(data=data, encoding=encoding)])
                history = channel.history()
                message = history.items[0]
                self.assertEqual(message.data, expected_value)
                self.assertEqual(type(message.data), type_mapping[expected_type])
