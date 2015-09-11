# -*- encoding: utf-8 -*-

import base64
import json
import logging
import unittest

import six
import mock
import msgpack

from ably import AblyRest
from ably import ChannelOptions, CipherParams
from ably.util.crypto import get_cipher, get_default_params
from ably.types.message import Message

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestTextEncodersNoEncryption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"],
                            use_binary_protocol=False)

    def test_text_utf8(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', six.u('foó'))
            _, kwargs = post_mock.call_args
            self.assertEqual(json.loads(kwargs['body'])['data'], six.u('foó'))
            self.assertEqual(json.loads(kwargs['body']).get('encoding', '').strip('/'),
                             'utf-8')

    def test_with_binary_type(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', six.b('foo'))
            _, kwargs = post_mock.call_args
            raw_data = json.loads(kwargs['body'])['data']
            self.assertEqual(base64.b64decode(raw_data.encode('ascii')),
                             six.b('foo'))
            self.assertEqual(json.loads(kwargs['body'])['encoding'].strip('/'),
                             'base64')

    def test_with_json_dict_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = {six.u('foó'): six.u('bár')}
        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(json.loads(kwargs['body'])['data'])
            self.assertEqual(raw_data, data)
            self.assertEqual(json.loads(kwargs['body'])['encoding'].strip('/'),
                             'json')

    def test_with_json_list_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = [six.u('foó'), six.u('bár')]
        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(json.loads(kwargs['body'])['data'])
            self.assertEqual(raw_data, data)
            self.assertEqual(json.loads(kwargs['body'])['encoding'].strip('/'),
                             'json')

    def test_text_utf8_decode(self):
        channel = self.ably.channels["persisted:stringdecode"]

        channel.publish('event', six.u('fóo'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.u('fóo'))
        self.assertIsInstance(message.data, six.text_type)
        self.assertFalse(message.encoding)

    def test_with_binary_type_decode(self):
        channel = self.ably.channels["persisted:binarydecode"]

        channel.publish('event', six.b('foob'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.b('foob'))
        self.assertIsInstance(message.data, six.binary_type)
        self.assertFalse(message.encoding)

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels["persisted:jsondict"]
        data = {six.u('foó'): six.u('bár')}
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels["persisted:jsonarray"]
        data = [six.u('foó'), six.u('bár')]
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)

    def test_decode_with_invalid_encoding(self):
        data = six.u('foó')
        encoded = base64.b64encode(data.encode('utf-8'))
        decoded_data = Message.decode(encoded, 'foo/bar/utf-8/base64')
        self.assertEqual(decoded_data['data'], data)
        self.assertEqual(decoded_data['encoding'], 'foo/bar')


class TestTextEncodersEncryption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"],
                            use_binary_protocol=False)
        cls.cipher_params = CipherParams(secret_key='keyfordecrypt_16',
                                         algorithm='aes')

    def decrypt(self, payload, options={}):
        ciphertext = base64.b64decode(payload.encode('ascii'))
        cipher = get_cipher(get_default_params('keyfordecrypt_16'))
        return cipher.decrypt(ciphertext)

    def test_text_utf8(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', six.u('fóo'))
            _, kwargs = post_mock.call_args
            self.assertEquals(json.loads(kwargs['body'])['encoding'].strip('/'),
                              'utf-8/cipher+aes-128-cbc/base64')
            data = self.decrypt(json.loads(kwargs['body'])['data']).decode('utf-8')
            self.assertEquals(data, six.u('fóo'))

    def test_with_binary_type(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))

        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', six.b('foo'))
            _, kwargs = post_mock.call_args

            self.assertEquals(json.loads(kwargs['body'])['encoding'].strip('/'),
                              'cipher+aes-128-cbc/base64')
            data = self.decrypt(json.loads(kwargs['body'])['data'])
            self.assertEqual(data, six.b('foo'))
            self.assertIsInstance(data, six.binary_type)

    def test_with_json_dict_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = {six.u('foó'): six.u('bár')}
        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            self.assertEquals(json.loads(kwargs['body'])['encoding'].strip('/'),
                              'json/utf-8/cipher+aes-128-cbc/base64')
            raw_data = self.decrypt(json.loads(kwargs['body'])['data']).decode('ascii')
            self.assertEqual(json.loads(raw_data), data)

    def test_with_json_list_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = [six.u('foó'), six.u('bár')]
        with mock.patch('ably.rest.rest.Http.post') as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            self.assertEquals(json.loads(kwargs['body'])['encoding'].strip('/'),
                              'json/utf-8/cipher+aes-128-cbc/base64')
            raw_data = self.decrypt(json.loads(kwargs['body'])['data']).decode('ascii')
            self.assertEqual(json.loads(raw_data), data)

    def test_text_utf8_decode(self):
        channel = self.ably.channels.get("persisted:enc_stringdecode",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        channel.publish('event', six.u('foó'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.u('foó'))
        self.assertIsInstance(message.data, six.text_type)
        self.assertFalse(message.encoding)

    def test_with_binary_type_decode(self):
        channel = self.ably.channels.get("persisted:enc_binarydecode",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))

        channel.publish('event', six.b('foob'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.b('foob'))
        self.assertIsInstance(message.data, six.binary_type)
        self.assertFalse(message.encoding)

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_jsondict",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = {six.u('foó'): six.u('bár')}
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_list",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = [six.u('foó'), six.u('bár')]
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)


class TestBinaryEncodersNoEncryption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"])

    def decode(self, data):
        return msgpack.unpackb(data, encoding='utf-8')

    def test_text_utf8(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', six.u('foó'))
            _, kwargs = post_mock.call_args
            self.assertEqual(self.decode(kwargs['body'])['data'], six.u('foó'))
            self.assertEqual(self.decode(kwargs['body']).get('encoding', '').strip('/'), '')

    def test_with_binary_type(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', six.b('foo'))
            _, kwargs = post_mock.call_args
            self.assertEqual(self.decode(kwargs['body'])['data'], six.b('foo'))
            self.assertEqual(self.decode(kwargs['body']).get('encoding', '').strip('/'), '')

    def test_with_json_dict_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = {six.u('foó'): six.u('bár')}
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(self.decode(kwargs['body'])['data'])
            self.assertEqual(raw_data, data)
            self.assertEqual(self.decode(kwargs['body'])['encoding'].strip('/'),
                             'json')

    def test_with_json_list_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = [six.u('foó'), six.u('bár')]
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(self.decode(kwargs['body'])['data'])
            self.assertEqual(raw_data, data)
            self.assertEqual(self.decode(kwargs['body'])['encoding'].strip('/'),
                             'json')

    def test_text_utf8_decode(self):
        channel = self.ably.channels["persisted:stringdecode-bin"]

        channel.publish('event', six.u('fóo'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.u('fóo'))
        self.assertIsInstance(message.data, six.text_type)
        self.assertFalse(message.encoding)

    def test_with_binary_type_decode(self):
        channel = self.ably.channels["persisted:binarydecode-bin"]

        channel.publish('event', six.b('foob'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.b('foob'))
        self.assertIsInstance(message.data, six.binary_type)
        self.assertFalse(message.encoding)

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels["persisted:jsondict-bin"]
        data = {six.u('foó'): six.u('bár')}
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels["persisted:jsonarray-bin"]
        data = [six.u('foó'), six.u('bár')]
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)


class TesBinaryEncodersEncryption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"])
        cls.cipher_params = CipherParams(secret_key='keyfordecrypt_16',
                                         algorithm='aes')

    def decrypt(self, payload, options={}):
        cipher = get_cipher(get_default_params('keyfordecrypt_16'))
        return cipher.decrypt(payload)

    def decode(self, data):
        return msgpack.unpackb(data, encoding='utf-8')

    def test_text_utf8(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', six.u('fóo'))
            _, kwargs = post_mock.call_args
            self.assertEquals(self.decode(kwargs['body'])['encoding'].strip('/'),
                              'utf-8/cipher+aes-128-cbc')
            data = self.decrypt(self.decode(kwargs['body'])['data']).decode('utf-8')
            self.assertEquals(data, six.u('fóo'))

    def test_with_binary_type(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', six.b('foo'))
            _, kwargs = post_mock.call_args

            self.assertEquals(self.decode(kwargs['body'])['encoding'].strip('/'),
                              'cipher+aes-128-cbc')
            data = self.decrypt(self.decode(kwargs['body'])['data'])
            self.assertEqual(data, six.b('foo'))
            self.assertIsInstance(data, six.binary_type)

    def test_with_json_dict_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = {six.u('foó'): six.u('bár')}
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            self.assertEquals(self.decode(kwargs['body'])['encoding'].strip('/'),
                              'json/utf-8/cipher+aes-128-cbc')
            raw_data = self.decrypt(self.decode(kwargs['body'])['data']).decode('ascii')
            self.assertEqual(json.loads(raw_data), data)

    def test_with_json_list_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = [six.u('foó'), six.u('bár')]
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            self.assertEquals(self.decode(kwargs['body'])['encoding'].strip('/'),
                              'json/utf-8/cipher+aes-128-cbc')
            raw_data = self.decrypt(self.decode(kwargs['body'])['data']).decode('ascii')
            self.assertEqual(json.loads(raw_data), data)

    def test_text_utf8_decode(self):
        channel = self.ably.channels.get("persisted:enc_stringdecode-bin",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        channel.publish('event', six.u('foó'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.u('foó'))
        self.assertIsInstance(message.data, six.text_type)
        self.assertFalse(message.encoding)

    def test_with_binary_type_decode(self):
        channel = self.ably.channels.get("persisted:enc_binarydecode-bin",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))

        channel.publish('event', six.b('foob'))
        message = channel.history().items[0]
        self.assertEqual(message.data, six.b('foob'))
        self.assertIsInstance(message.data, six.binary_type)
        self.assertFalse(message.encoding)

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_jsondict-bin",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = {six.u('foó'): six.u('bár')}
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_list-bin",
                                         options=ChannelOptions(
                                            encrypted=True,
                                            cipher_params=self.cipher_params))
        data = [six.u('foó'), six.u('bár')]
        channel.publish('event', data)
        message = channel.history().items[0]
        self.assertEqual(message.data, data)
        self.assertFalse(message.encoding)
