from __future__ import absolute_import

import json
import os
import logging
import unittest
import base64

import six

from ably import AblyException
from ably import AblyRest
from ably import ChannelOptions
from ably.types.message import Message
from ably.util.crypto import CipherParams, get_cipher, get_default_params

from Crypto import Random

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestRestCrypto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = {
            "key": test_vars["keys"][0]["key_str"],
            "host": test_vars["host"],
            "port": test_vars["port"],
            "tls_port": test_vars["tls_port"],
            "tls": test_vars["tls"],
            "use_binary_protocol": False
        }
        cls.ably = AblyRest(**options)
        cls.ably2 = AblyRest(**options)

    def test_cbc_channel_cipher(self):
        key = six.b(
                '\x93\xe3\x5c\xc9\x77\x53\xfd\x1a'
                '\x79\xb4\xd8\x84\xe7\xdc\xfd\xdf'
        )
        iv = six.b(
                '\x28\x4c\xe4\x8d\x4b\xdc\x9d\x42'
                '\x8a\x77\x6b\x53\x2d\xc7\xb5\xc0'
        )
        log.debug("KEY_LEN: %d" % len(key))
        log.debug("IV_LEN: %d" % len(iv))
        cipher = get_cipher(CipherParams(secret_key=key, iv=iv))

        plaintext = six.b("The quick brown fox")
        expected_ciphertext = six.b(
                '\x28\x4c\xe4\x8d\x4b\xdc\x9d\x42'
                '\x8a\x77\x6b\x53\x2d\xc7\xb5\xc0'
                '\x83\x5c\xcf\xce\x0c\xfd\xbe\x37'
                '\xb7\x92\x12\x04\x1d\x45\x68\xa4'
                '\xdf\x7f\x6e\x38\x17\x4a\xff\x50'
                '\x73\x23\xbb\xca\x16\xb0\xe2\x84'
        )

        actual_ciphertext = cipher.encrypt(plaintext)

        self.assertEqual(expected_ciphertext, actual_ciphertext)

    def test_crypto_publish_text(self):
        channel_options = ChannelOptions(encrypted=True,
                                         cipher_params=get_default_params())
        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_publish_text", channel_options)

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        history = publish0.history()
        messages = history.items
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(4, len(messages), msg="Expected 4 messages")

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

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

    def test_crypto_publish_text_256(self):
        rndfile = Random.new()
        key = rndfile.read(32)
        cipher_params = get_default_params(key=key)
        channel_options = ChannelOptions(encrypted=True,
                                         cipher_params=cipher_params)

        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_publish_text_256", channel_options)

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        history = publish0.history()
        messages = history.items
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(4, len(messages), msg="Expected 4 messages")

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

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

    def test_crypto_publish_key_mismatch(self):
        channel_options = ChannelOptions(encrypted=True,
                                         cipher_params=get_default_params())
        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_publish_key_mismatch", channel_options)

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        channel_options = ChannelOptions(encrypted=True,
                                         cipher_params=get_default_params())
        rx_channel = TestRestCrypto.ably2.channels.get("persisted:crypto_publish_key_mismatch", channel_options)

        try:
            with self.assertRaises(AblyException) as cm:
                messages = rx_channel.history()
        except Exception as e:
            log.debug('test_crypto_publish_key_mismatch_fail: rx_channel.history not creating exception')
            log.debug(messages.items[0].data)

            raise(e)

        the_exception = cm.exception
        self.assertEqual('invalid-padding', the_exception.message)

    def test_crypto_send_unencrypted(self):
        publish0 = TestRestCrypto.ably.channels['persisted:crypto_send_unencrypted']
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        rx_options = ChannelOptions(encrypted=True,
                                    cipher_params=get_default_params())
        rx_channel = TestRestCrypto.ably2.channels.get('persisted:crypto_send_unencrypted', rx_options)

        history = rx_channel.history()
        messages = history.items
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(4, len(messages), msg="Expected 4 messages")

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

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

    def test_crypto_encrypted_unhandled(self):
        key = '0123456789abcdef'
        data = six.u('foobar')
        channel_options = ChannelOptions(encrypted=True,
                                         cipher_params=get_default_params(key))
        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_send_encrypted_unhandled", channel_options)

        publish0.publish("publish0", data)

        rx_channel = TestRestCrypto.ably2.channels['persisted:crypto_send_encrypted_unhandled']
        history = rx_channel.history()
        message = history.items[0]
        cipher = get_cipher(get_default_params(key))
        self.assertEqual(cipher.decrypt(message.data).decode(), data)
        self.assertEqual(message.encoding, 'utf-8/cipher+aes-128-cbc')

    def test_cipher_params(self):
        params = CipherParams(secret_key='0123456789abcdef')
        self.assertEqual(params.algorithm, 'AES')
        self.assertEqual(params.mode, 'CBC')
        self.assertEqual(params.key_length, 128)

        params = CipherParams(secret_key='0123456789abcdef' * 2)
        self.assertEqual(params.algorithm, 'AES')
        self.assertEqual(params.mode, 'CBC')
        self.assertEqual(params.key_length, 256)


class AbstractTestCryptoWithFixture(object):

    @classmethod
    def setUpClass(cls):
        with open(os.path.dirname(__file__) + '/../../submodules/test-resources/%s' % cls.fixture_file, 'r') as f:
            cls.fixture = json.loads(f.read())
            cls.params = {
                'secret_key': base64.b64decode(cls.fixture['key'].encode('ascii')),
                'mode': cls.fixture['mode'],
                'algorithm': cls.fixture['algorithm'],
                'iv': base64.b64decode(cls.fixture['iv'].encode('ascii')),
            }
            cls.cipher_params = CipherParams(**cls.params)
            cls.cipher = get_cipher(cls.cipher_params)
            cls.items = cls.fixture['items']

    def get_encoded(self, encoded_item):
        if encoded_item.get('encoding') == 'base64':
            return base64.b64decode(encoded_item['data'].encode('ascii'))
        elif encoded_item.get('encoding') == 'json':
            return json.loads(encoded_item['data'])
        return encoded_item['data']

    def test_decode(self):
        for item in self.items:
            self.assertEqual(item['encoded']['name'], item['encrypted']['name'])
            message = Message.from_dict(item['encrypted'], self.cipher)
            self.assertEqual(message.encoding, '')
            expected_data = self.get_encoded(item['encoded'])
            self.assertEqual(expected_data, message.data)

    def test_encode(self):
        for item in self.items:
            # need to reset iv
            self.cipher_params = CipherParams(**self.params)
            self.cipher = get_cipher(self.cipher_params)
            data = self.get_encoded(item['encoded'])
            expected = item['encrypted']
            message = Message(item['encoded']['name'], data)
            message.encrypt(self.cipher)
            as_dict = message.as_dict()
            self.assertEqual(as_dict['data'], expected['data'])
            self.assertEqual(as_dict['encoding'], expected['encoding'])


class TestCryptoWithFixture128(AbstractTestCryptoWithFixture, unittest.TestCase):
    fixture_file = 'crypto-data-128.json'


class TestCryptoWithFixture256(AbstractTestCryptoWithFixture, unittest.TestCase):
    fixture_file = 'crypto-data-256.json'
