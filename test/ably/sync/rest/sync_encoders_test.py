import base64
import json
import logging
import sys

import mock
import msgpack

from ably.sync import CipherParams
from ably.sync.util.crypto import get_cipher
from ably.sync.types.message import Message

from test.ably.sync.testapp import TestApp
from test.ably.sync.utils import BaseAsyncTestCase

if sys.version_info >= (3, 8):
    from unittest.mock import Mock
else:
    from mock import Mock

log = logging.getLogger(__name__)


class TestTextEncodersNoEncryption(BaseAsyncTestCase):
    def setUp(self):
        self.ably = TestApp.get_ably_rest(use_binary_protocol=False)

    def tearDown(self):
        self.ably.close()

    def test_text_utf8(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', 'foó')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['data'] == 'foó'
            assert not json.loads(kwargs['body']).get('encoding', '')

    def test_str(self):
        # This test only makes sense for py2
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', 'foo')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['data'] == 'foo'
            assert not json.loads(kwargs['body']).get('encoding', '')

    def test_with_binary_type(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args
            raw_data = json.loads(kwargs['body'])['data']
            assert base64.b64decode(raw_data.encode('ascii')) == bytearray(b'foo')
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'base64'

    def test_with_bytes_type(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', b'foo')
            _, kwargs = post_mock.call_args
            raw_data = json.loads(kwargs['body'])['data']
            assert base64.b64decode(raw_data.encode('ascii')) == bytearray(b'foo')
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'base64'

    def test_with_json_dict_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(json.loads(kwargs['body'])['data'])
            assert raw_data == data
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json'

    def test_with_json_list_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(json.loads(kwargs['body'])['data'])
            assert raw_data == data
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json'

    def test_text_utf8_decode(self):
        channel = self.ably.channels["persisted:stringdecode"]

        channel.publish('event', 'fóo')
        history = channel.history()
        message = history.items[0]
        assert message.data == 'fóo'
        assert isinstance(message.data, str)
        assert not message.encoding

    def test_text_str_decode(self):
        channel = self.ably.channels["persisted:stringnonutf8decode"]

        channel.publish('event', 'foo')
        history = channel.history()
        message = history.items[0]
        assert message.data == 'foo'
        assert isinstance(message.data, str)
        assert not message.encoding

    def test_with_binary_type_decode(self):
        channel = self.ably.channels["persisted:binarydecode"]

        channel.publish('event', bytearray(b'foob'))
        history = channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert isinstance(message.data, bytearray)
        assert not message.encoding

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels["persisted:jsondict"]
        data = {'foó': 'bár'}
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels["persisted:jsonarray"]
        data = ['foó', 'bár']
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    def test_decode_with_invalid_encoding(self):
        data = 'foó'
        encoded = base64.b64encode(data.encode('utf-8'))
        decoded_data = Message.decode(encoded, 'foo/bar/utf-8/base64')
        assert decoded_data['data'] == data
        assert decoded_data['encoding'] == 'foo/bar'


class TestTextEncodersEncryption(BaseAsyncTestCase):
    def setUp(self):
        self.ably = TestApp.get_ably_rest(use_binary_protocol=False)
        self.cipher_params = CipherParams(secret_key='keyfordecrypt_16',
                                          algorithm='aes')

    def tearDown(self):
        self.ably.close()

    def decrypt(self, payload, options=None):
        if options is None:
            options = {}
        ciphertext = base64.b64decode(payload.encode('ascii'))
        cipher = get_cipher({'key': b'keyfordecrypt_16'})
        return cipher.decrypt(ciphertext)

    def test_text_utf8(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)
        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', 'fóo')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'utf-8/cipher+aes-128-cbc/base64'
            data = self.decrypt(json.loads(kwargs['body'])['data']).decode('utf-8')
            assert data == 'fóo'

    def test_str(self):
        # This test only makes sense for py2
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', 'foo')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['data'] == 'foo'
            assert not json.loads(kwargs['body']).get('encoding', '')

    def test_with_binary_type(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)

        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args

            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'cipher+aes-128-cbc/base64'
            data = self.decrypt(json.loads(kwargs['body'])['data'])
            assert data == bytearray(b'foo')
            assert isinstance(data, bytearray)

    def test_with_json_dict_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc/base64'
            raw_data = self.decrypt(json.loads(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    def test_with_json_list_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post', new_callable=Mock) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc/base64'
            raw_data = self.decrypt(json.loads(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    def test_text_utf8_decode(self):
        channel = self.ably.channels.get("persisted:enc_stringdecode",
                                         cipher=self.cipher_params)
        channel.publish('event', 'foó')
        history = channel.history()
        message = history.items[0]
        assert message.data == 'foó'
        assert isinstance(message.data, str)
        assert not message.encoding

    def test_with_binary_type_decode(self):
        channel = self.ably.channels.get("persisted:enc_binarydecode",
                                         cipher=self.cipher_params)

        channel.publish('event', bytearray(b'foob'))
        history = channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert isinstance(message.data, bytearray)
        assert not message.encoding

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_jsondict",
                                         cipher=self.cipher_params)
        data = {'foó': 'bár'}
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_list",
                                         cipher=self.cipher_params)
        data = ['foó', 'bár']
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding


class TestBinaryEncodersNoEncryption(BaseAsyncTestCase):

    def setUp(self):
        self.ably = TestApp.get_ably_rest()

    def tearDown(self):
        self.ably.close()

    def decode(self, data):
        return msgpack.unpackb(data)

    def test_text_utf8(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', 'foó')
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['data'] == 'foó'
            assert self.decode(kwargs['body']).get('encoding', '').strip('/') == ''

    def test_with_binary_type(self):
        channel = self.ably.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['data'] == bytearray(b'foo')
            assert self.decode(kwargs['body']).get('encoding', '').strip('/') == ''

    def test_with_json_dict_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(self.decode(kwargs['body'])['data'])
            assert raw_data == data
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json'

    def test_with_json_list_data(self):
        channel = self.ably.channels["persisted:publish"]
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(self.decode(kwargs['body'])['data'])
            assert raw_data == data
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json'

    def test_text_utf8_decode(self):
        channel = self.ably.channels["persisted:stringdecode-bin"]

        channel.publish('event', 'fóo')
        history = channel.history()
        message = history.items[0]
        assert message.data == 'fóo'
        assert isinstance(message.data, str)
        assert not message.encoding

    def test_with_binary_type_decode(self):
        channel = self.ably.channels["persisted:binarydecode-bin"]

        channel.publish('event', bytearray(b'foob'))
        history = channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert not message.encoding

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels["persisted:jsondict-bin"]
        data = {'foó': 'bár'}
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels["persisted:jsonarray-bin"]
        data = ['foó', 'bár']
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding


class TestBinaryEncodersEncryption(BaseAsyncTestCase):

    def setUp(self):
        self.ably = TestApp.get_ably_rest()
        self.cipher_params = CipherParams(secret_key='keyfordecrypt_16', algorithm='aes')

    def tearDown(self):
        self.ably.close()

    def decrypt(self, payload, options=None):
        if options is None:
            options = {}
        cipher = get_cipher({'key': b'keyfordecrypt_16'})
        return cipher.decrypt(payload)

    def decode(self, data):
        return msgpack.unpackb(data)

    def test_text_utf8(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', 'fóo')
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'utf-8/cipher+aes-128-cbc'
            data = self.decrypt(self.decode(kwargs['body'])['data']).decode('utf-8')
            assert data == 'fóo'

    def test_with_binary_type(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args

            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'cipher+aes-128-cbc'
            data = self.decrypt(self.decode(kwargs['body'])['data'])
            assert data == bytearray(b'foo')
            assert isinstance(data, bytearray)

    def test_with_json_dict_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc'
            raw_data = self.decrypt(self.decode(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    def test_with_json_list_data(self):
        channel = self.ably.channels.get("persisted:publish_enc",
                                         cipher=self.cipher_params)
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc'
            raw_data = self.decrypt(self.decode(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    def test_text_utf8_decode(self):
        channel = self.ably.channels.get("persisted:enc_stringdecode-bin",
                                         cipher=self.cipher_params)
        channel.publish('event', 'foó')
        history = channel.history()
        message = history.items[0]
        assert message.data == 'foó'
        assert isinstance(message.data, str)
        assert not message.encoding

    def test_with_binary_type_decode(self):
        channel = self.ably.channels.get("persisted:enc_binarydecode-bin",
                                         cipher=self.cipher_params)

        channel.publish('event', bytearray(b'foob'))
        history = channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert isinstance(message.data, bytearray)
        assert not message.encoding

    def test_with_json_dict_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_jsondict-bin",
                                         cipher=self.cipher_params)
        data = {'foó': 'bár'}
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    def test_with_json_list_data_decode(self):
        channel = self.ably.channels.get("persisted:enc_list-bin",
                                         cipher=self.cipher_params)
        data = ['foó', 'bár']
        channel.publish('event', data)
        history = channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding
