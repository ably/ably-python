from __future__ import absolute_import

import logging
import time
import unittest

import six

from ably import AblyException
from ably import AblyRest
from ably import ChannelOptions
from ably import Options
from ably.util.crypto import CipherParams, get_cipher

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)

class TestRestCrypto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        options = Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"],
                use_text_protocol=True)
        cls.ably = AblyRest(options)

    def test_cbc_channel_cipher(self):
        key = bytes([
            0x93, 0xe3, 0x5c, 0xc9, 0x77, 0x53, 0xfd, 0x1a,
            0x79, 0xb4, 0xd8, 0x84, 0xe7, 0xdc, 0xfd, 0xdf,
        ])
        iv = bytes([
            0x28, 0x4c, 0xe4, 0x8d, 0x4b, 0xdc, 0x9d, 0x42,
            0x8a, 0x77, 0x6b, 0x53, 0x2d, 0xc7, 0xb5, 0xc0,
        ])
        log.debug("KEYLEN: %d" % len(key))
        log.debug("IVLEN: %d" % len(iv))
        cipher = get_cipher(CipherParams(secret_key=key, iv=iv))

        plaintext = six.b("The quick brown fox")
        expected_ciphertext = bytes([
            0x28, 0x4c, 0xe4, 0x8d, 0x4b, 0xdc, 0x9d, 0x42,
            0x8a, 0x77, 0x6b, 0x53, 0x2d, 0xc7, 0xb5, 0xc0,
            0x83, 0x5c, 0xcf, 0xce, 0x0c, 0xfd, 0xbe, 0x37,
            0xb7, 0x92, 0x12, 0x04, 0x1d, 0x45, 0x68, 0xa4,
            0xdf, 0x7f, 0x6e, 0x38, 0x17, 0x4a, 0xff, 0x50,
            0x73, 0x23, 0xbb, 0xca, 0x16, 0xb0, 0xe2, 0x84,
        ])
        
        actual_ciphertext = cipher.encrypt(plaintext)

        self.assertEquals(expected_ciphertext, actual_ciphertext)

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

        time.sleep(16)

        history = publish0.history()
        messages = history.current
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEquals(7, len(messages), msg="Expected 7 messages")

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        self.assertEquals(True, message_contents["publish0"],
                msg="Expect publish0 to be Boolean(true)")
        self.assertEquals(24, int(message_contents["publish1"]),
                msg="Expect publish1 to be Int(24)")
        self.assertEquals(24.234, float(message_contents["publish2"]),
                msg="Expect publish2 to be Double(24.234)")
        self.assertEquals(six.u("This is a string message payload"),
                message_contents["publish3"],
                msg="Expect publish3 to be expected String)")
        self.assertEquals(b"This is a byte[] message payload",
                message_contents["publish4"],
                msg="Expect publish4 to be expected byte[]. Actual: %s" % str(message_contents['publish4']))
        self.assertEquals({"test": "This is a JSONObject message payload"},
                message_contents["publish5"],
                msg="Expect publish5 to be expected JSONObject")
        self.assertEquals(["This is a JSONArray message payload"],
                message_contents["publish6"],
                msg="Expect publish6 to be expected JSONObject")
