from __future__ import absolute_import

import logging
import time
import unittest

import six

from ably import AblyException
from ably import AblyRest
from ably import ChannelOptions
from ably import Options
from ably.util.crypto import CipherParams, CipherData, get_cipher, get_default_params

from Crypto import Random

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)

class TestRestCrypto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = Options(key=test_vars["keys"][0]["key_str"],
                          host=test_vars["host"],
                          port=test_vars["port"],
                          tls_port=test_vars["tls_port"],
                          tls=test_vars["tls"],
                          use_text_protocol=True)
        cls.ably = AblyRest(options=options)
        cls.ably2 = AblyRest(options=options)

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
        channel_options = ChannelOptions(encrypted=True)
        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_publish_text", channel_options)

        publish0.publish("publish0", True)
        publish0.publish("publish1", 24)
        publish0.publish("publish2", 24.234)
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

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

    def test_crypto_publish_text_256(self):
        rndfile = Random.new()
        key = rndfile.read(32)
        cipher_params = get_default_params(key=key)
        channel_options = ChannelOptions(encrypted=True, cipher_params=cipher_params)

        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_publish_text_256", channel_options)

        publish0.publish("publish0", True)
        publish0.publish("publish1", 24)
        publish0.publish("publish2", 24.234)
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

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

    def test_crypto_publish_key_mismatch(self):
        channel_options = ChannelOptions(encrypted=True)
        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_publish_key_mismatch", channel_options)

        publish0.publish("publish0", True)
        publish0.publish("publish1", 24)
        publish0.publish("publish2", 24.234)
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        rx_channel = TestRestCrypto.ably2.channels.get("persisted:crypto_publish_key_mismatch", channel_options)
        
        try:
            with self.assertRaises(AblyException) as cm:
                messages = rx_channel.history()                
        except Exception as e:
            log.debug('test_crypto_publish_key_mismatch_fail: rx_channel.history not creating exception')
            log.debug(messages.current[0].data)
            log.debug(messages.current[0].decrypt())

            raise(e)


        the_exception = cm.exception
        self.assertEqual('invalid-padding', the_exception.reason)

    def test_crypto_send_unencrypted(self):
        publish0 = TestRestCrypto.ably.channels['persisted:crypto_send_unencrypted']
        publish0.publish("publish0", True)
        publish0.publish("publish1", 24)
        publish0.publish("publish2", 24.234)
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        rx_options = ChannelOptions(encrypted=True)
        rx_channel = TestRestCrypto.ably2.channels.get('persisted:crypto_send_unencrypted', rx_options)

        history = rx_channel.history()
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

    def test_crypto_send_encrypted_unhandled(self):
        channel_options = ChannelOptions(encrypted=True)
        publish0 = TestRestCrypto.ably.channels.get("persisted:crypto_send_encrypted_unhandled", channel_options)

        publish0.publish("publish0", True)
        publish0.publish("publish1", 24)
        publish0.publish("publish2", 24.234)
        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        rx_channel = TestRestCrypto.ably2.channels['persisted:crypto_send_encrypted_unhandled']
        history = rx_channel.history()
        messages = history.current
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEqual(7, len(messages), msg="Expected 7 messages")

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        for k, v in six.iteritems(message_contents):
            if (k == "publish0"):
                self.assertEqual(True, v, "Expect publish0 to be BOOL(True)")
                continue
            self.assertTrue(isinstance(v, CipherData))

