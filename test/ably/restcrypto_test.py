from __future__ import absolute_import

import json
import os
import logging
import base64

import pytest
import six

from ably import AblyException
from ably.types.message import Message
from ably.util.crypto import CipherParams, get_cipher, generate_random_key, get_default_params

from Crypto import Random

from test.ably.restsetup import RestSetup
from test.ably.utils import dont_vary_protocol, VaryByProtocolTestsMetaclass, BaseTestCase

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestCrypto(BaseTestCase):

    def setUp(self):
        self.ably = RestSetup.get_ably_rest()
        self.ably2 = RestSetup.get_ably_rest()

    def per_protocol_setup(self, use_binary_protocol):
        # This will be called every test that vary by protocol for each protocol
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.ably2.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    @dont_vary_protocol
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
        cipher = get_cipher({'key': key, 'iv': iv})

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

        assert expected_ciphertext == actual_ciphertext

    def test_crypto_publish(self):
        channel_name = self.get_channel_name('persisted:crypto_publish_text')
        publish0 = self.ably.channels.get(channel_name, cipher={'key': generate_random_key()})

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        history = publish0.history()
        messages = history.items
        assert messages is not None, "Expected non-None messages"
        assert 4 == len(messages), "Expected 4 messages"

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        assert six.u("This is a string message payload") == message_contents["publish3"], "Expect publish3 to be expected String)"
        assert b"This is a byte[] message payload" == message_contents["publish4"], "Expect publish4 to be expected byte[]. Actual: %s" % str(message_contents['publish4'])
        assert {"test": "This is a JSONObject message payload"} == message_contents["publish5"], "Expect publish5 to be expected JSONObject"
        assert ["This is a JSONArray message payload"] == message_contents["publish6"], "Expect publish6 to be expected JSONObject"

    def test_crypto_publish_256(self):
        rndfile = Random.new()
        key = rndfile.read(32)
        channel_name = 'persisted:crypto_publish_text_256'
        channel_name += '_bin' if self.use_binary_protocol else '_text'

        publish0 = self.ably.channels.get(channel_name, cipher={'key': key})

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        history = publish0.history()
        messages = history.items
        assert messages is not None, "Expected non-None messages"
        assert 4 == len(messages), "Expected 4 messages"

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        assert six.u("This is a string message payload") == message_contents["publish3"], "Expect publish3 to be expected String)"
        assert b"This is a byte[] message payload" == message_contents["publish4"], "Expect publish4 to be expected byte[]. Actual: %s" % str(message_contents['publish4'])
        assert {"test": "This is a JSONObject message payload"} == message_contents["publish5"], "Expect publish5 to be expected JSONObject"
        assert ["This is a JSONArray message payload"] == message_contents["publish6"], "Expect publish6 to be expected JSONObject"

    def test_crypto_publish_key_mismatch(self):
        channel_name = self.get_channel_name('persisted:crypto_publish_key_mismatch')

        publish0 = self.ably.channels.get(channel_name, cipher={'key': generate_random_key()})

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        rx_channel = self.ably2.channels.get(channel_name, cipher={'key': generate_random_key()})

        with pytest.raises(AblyException) as excinfo:
            rx_channel.history()

        message = excinfo.value.message
        assert (
            'invalid-padding' == message or
            message.startswith("UnicodeDecodeError: 'utf8'") or
            message.startswith("UnicodeDecodeError: 'utf-8'")
        )

    def test_crypto_send_unencrypted(self):
        channel_name = self.get_channel_name('persisted:crypto_send_unencrypted')
        publish0 = self.ably.channels[channel_name]

        publish0.publish("publish3", six.u("This is a string message payload"))
        publish0.publish("publish4", six.b("This is a byte[] message payload"))
        publish0.publish("publish5", {"test": "This is a JSONObject message payload"})
        publish0.publish("publish6", ["This is a JSONArray message payload"])

        rx_channel = self.ably2.channels.get(channel_name, cipher={'key': generate_random_key()})

        history = rx_channel.history()
        messages = history.items
        assert messages is not None, "Expected non-None messages"
        assert 4 == len(messages), "Expected 4 messages"

        message_contents = dict((m.name, m.data) for m in messages)
        log.debug("message_contents: %s" % str(message_contents))

        assert six.u("This is a string message payload") == message_contents["publish3"], "Expect publish3 to be expected String)"
        assert b"This is a byte[] message payload" == message_contents["publish4"], "Expect publish4 to be expected byte[]. Actual: %s" % str(message_contents['publish4'])
        assert {"test": "This is a JSONObject message payload"} == message_contents["publish5"], "Expect publish5 to be expected JSONObject"
        assert ["This is a JSONArray message payload"] == message_contents["publish6"], "Expect publish6 to be expected JSONObject"

    def test_crypto_encrypted_unhandled(self):
        channel_name = self.get_channel_name('persisted:crypto_send_encrypted_unhandled')
        key = six.b('0123456789abcdef')
        data = six.u('foobar')
        publish0 = self.ably.channels.get(channel_name, cipher={'key': key})

        publish0.publish("publish0", data)

        rx_channel = self.ably2.channels[channel_name]
        history = rx_channel.history()
        message = history.items[0]
        cipher = get_cipher(get_default_params({'key': key}))
        assert cipher.decrypt(message.data).decode() == data
        assert message.encoding == 'utf-8/cipher+aes-128-cbc'

    @dont_vary_protocol
    def test_cipher_params(self):
        params = CipherParams(secret_key='0123456789abcdef')
        assert params.algorithm == 'AES'
        assert params.mode == 'CBC'
        assert params.key_length == 128

        params = CipherParams(secret_key='0123456789abcdef' * 2)
        assert params.algorithm == 'AES'
        assert params.mode == 'CBC'
        assert params.key_length == 256


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

    # TM3
    def test_decode(self):
        for item in self.items:
            assert item['encoded']['name'] == item['encrypted']['name']
            message = Message.from_encoded(item['encrypted'], self.cipher)
            assert message.encoding == ''
            expected_data = self.get_encoded(item['encoded'])
            assert expected_data == message.data

    # TM3
    def test_decode_array(self):
        items_encrypted = [item['encrypted'] for item in self.items]
        messages = Message.from_encoded_array(items_encrypted, self.cipher)
        for i, message in enumerate(messages):
            assert message.encoding == ''
            expected_data = self.get_encoded(self.items[i]['encoded'])
            assert expected_data == message.data

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
            assert as_dict['data'] == expected['data']
            assert as_dict['encoding'] == expected['encoding']


class TestCryptoWithFixture128(AbstractTestCryptoWithFixture, BaseTestCase):
    fixture_file = 'crypto-data-128.json'


class TestCryptoWithFixture256(AbstractTestCryptoWithFixture, BaseTestCase):
    fixture_file = 'crypto-data-256.json'
