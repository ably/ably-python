import base64
import json
import logging
import pytest

import mock
import msgpack

from ably import CipherParams
from ably.util.crypto import get_cipher
from ably.types.message import Message

from unittest.mock import AsyncMock

log = logging.getLogger(__name__)


@pytest.fixture(name="cipher_params")
def cipher_params_fixture():
    yield CipherParams(secret_key='keyfordecrypt_16',
                       algorithm='aes')


class TestTextEncodersNoEncryption:
    @pytest.mark.asyncio
    async def test_text_utf8(self, json_rest):
        channel = json_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', 'foó')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['data'] == 'foó'
            assert not json.loads(kwargs['body']).get('encoding', '')

    @pytest.mark.asyncio
    async def test_str(self, json_rest):
        # This test only makes sense for py2
        channel = json_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', 'foo')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['data'] == 'foo'
            assert not json.loads(kwargs['body']).get('encoding', '')

    @pytest.mark.asyncio
    async def test_with_binary_type(self, json_rest):
        channel = json_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args
            raw_data = json.loads(kwargs['body'])['data']
            assert base64.b64decode(raw_data.encode('ascii')) == bytearray(b'foo')
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'base64'

    @pytest.mark.asyncio
    async def test_with_bytes_type(self, json_rest):
        channel = json_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', b'foo')
            _, kwargs = post_mock.call_args
            raw_data = json.loads(kwargs['body'])['data']
            assert base64.b64decode(raw_data.encode('ascii')) == bytearray(b'foo')
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'base64'

    @pytest.mark.asyncio
    async def test_with_json_dict_data(self, json_rest):
        channel = json_rest.channels["persisted:publish"]
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(json.loads(kwargs['body'])['data'])
            assert raw_data == data
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json'

    @pytest.mark.asyncio
    async def test_with_json_list_data(self, json_rest):
        channel = json_rest.channels["persisted:publish"]
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(json.loads(kwargs['body'])['data'])
            assert raw_data == data
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json'

    @pytest.mark.asyncio
    async def test_text_utf8_decode(self, json_rest):
        channel = json_rest.channels["persisted:stringdecode"]

        await channel.publish('event', 'fóo')
        history = await channel.history()
        message = history.items[0]
        assert message.data == 'fóo'
        assert isinstance(message.data, str)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_text_str_decode(self, json_rest):
        channel = json_rest.channels["persisted:stringnonutf8decode"]

        await channel.publish('event', 'foo')
        history = await channel.history()
        message = history.items[0]
        assert message.data == 'foo'
        assert isinstance(message.data, str)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_binary_type_decode(self, json_rest):
        channel = json_rest.channels["persisted:binarydecode"]

        await channel.publish('event', bytearray(b'foob'))
        history = await channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert isinstance(message.data, bytearray)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_dict_data_decode(self, json_rest):
        channel = json_rest.channels["persisted:jsondict"]
        data = {'foó': 'bár'}
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_list_data_decode(self, json_rest):
        channel = json_rest.channels["persisted:jsonarray"]
        data = ['foó', 'bár']
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    def test_decode_with_invalid_encoding(self):
        data = 'foó'
        encoded = base64.b64encode(data.encode('utf-8'))
        decoded_data = Message.decode(encoded, 'foo/bar/utf-8/base64')
        assert decoded_data['data'] == data
        assert decoded_data['encoding'] == 'foo/bar'


class TestTextEncodersEncryption:
    def decrypt(self, payload, options=None):
        if options is None:
            options = {}
        ciphertext = base64.b64decode(payload.encode('ascii'))
        cipher = get_cipher({'key': b'keyfordecrypt_16'})
        return cipher.decrypt(ciphertext)

    @pytest.mark.asyncio
    async def test_text_utf8(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:publish_enc",
                                         cipher=cipher_params)
        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', 'fóo')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'utf-8/cipher+aes-128-cbc/base64'
            data = self.decrypt(json.loads(kwargs['body'])['data']).decode('utf-8')
            assert data == 'fóo'

    @pytest.mark.asyncio
    async def test_str(self, json_rest):
        # This test only makes sense for py2
        channel = json_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', 'foo')
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['data'] == 'foo'
            assert not json.loads(kwargs['body']).get('encoding', '')

    @pytest.mark.asyncio
    async def test_with_binary_type(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:publish_enc",
                                         cipher=cipher_params)

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args

            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'cipher+aes-128-cbc/base64'
            data = self.decrypt(json.loads(kwargs['body'])['data'])
            assert data == bytearray(b'foo')
            assert isinstance(data, bytearray)

    @pytest.mark.asyncio
    async def test_with_json_dict_data(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:publish_enc",
                                         cipher=cipher_params)
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc/base64'
            raw_data = self.decrypt(json.loads(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    @pytest.mark.asyncio
    async def test_with_json_list_data(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:publish_enc",
                                         cipher=cipher_params)
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert json.loads(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc/base64'
            raw_data = self.decrypt(json.loads(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    @pytest.mark.asyncio
    async def test_text_utf8_decode(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:enc_stringdecode",
                                         cipher=cipher_params)
        await channel.publish('event', 'foó')
        history = await channel.history()
        message = history.items[0]
        assert message.data == 'foó'
        assert isinstance(message.data, str)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_binary_type_decode(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:enc_binarydecode",
                                         cipher=cipher_params)

        await channel.publish('event', bytearray(b'foob'))
        history = await channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert isinstance(message.data, bytearray)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_dict_data_decode(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:enc_jsondict",
                                         cipher=cipher_params)
        data = {'foó': 'bár'}
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_list_data_decode(self, json_rest, cipher_params):
        channel = json_rest.channels.get("persisted:enc_list",
                                         cipher=cipher_params)
        data = ['foó', 'bár']
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding


class TestBinaryEncodersNoEncryption:
    def decode(self, data):
        return msgpack.unpackb(data)

    @pytest.mark.asyncio
    async def test_text_utf8(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', 'foó')
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['data'] == 'foó'
            assert self.decode(kwargs['body']).get('encoding', '').strip('/') == ''

    @pytest.mark.asyncio
    async def test_with_binary_type(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:publish"]

        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['data'] == bytearray(b'foo')
            assert self.decode(kwargs['body']).get('encoding', '').strip('/') == ''

    @pytest.mark.asyncio
    async def test_with_json_dict_data(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:publish"]
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(self.decode(kwargs['body'])['data'])
            assert raw_data == data
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json'

    @pytest.mark.asyncio
    async def test_with_json_list_data(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:publish"]
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            raw_data = json.loads(self.decode(kwargs['body'])['data'])
            assert raw_data == data
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json'

    @pytest.mark.asyncio
    async def test_text_utf8_decode(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:stringdecode-bin"]

        await channel.publish('event', 'fóo')
        history = await channel.history()
        message = history.items[0]
        assert message.data == 'fóo'
        assert isinstance(message.data, str)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_binary_type_decode(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:binarydecode-bin"]

        await channel.publish('event', bytearray(b'foob'))
        history = await channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_dict_data_decode(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:jsondict-bin"]
        data = {'foó': 'bár'}
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_list_data_decode(self, msgpack_rest):
        channel = msgpack_rest.channels["persisted:jsonarray-bin"]
        data = ['foó', 'bár']
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding


class TestBinaryEncodersEncryption:

    def decrypt(self, payload, options=None):
        if options is None:
            options = {}
        cipher = get_cipher({'key': b'keyfordecrypt_16'})
        return cipher.decrypt(payload)

    def decode(self, data):
        return msgpack.unpackb(data)

    @pytest.mark.asyncio
    async def test_text_utf8(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:publish_enc",
                                            cipher=cipher_params)
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', 'fóo')
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'utf-8/cipher+aes-128-cbc'
            data = self.decrypt(self.decode(kwargs['body'])['data']).decode('utf-8')
            assert data == 'fóo'

    @pytest.mark.asyncio
    async def test_with_binary_type(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:publish_enc",
                                            cipher=cipher_params)

        with mock.patch('ably.rest.rest.Http.post', new_callable=AsyncMock) as post_mock:
            await channel.publish('event', bytearray(b'foo'))
            _, kwargs = post_mock.call_args

            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'cipher+aes-128-cbc'
            data = self.decrypt(self.decode(kwargs['body'])['data'])
            assert data == bytearray(b'foo')
            assert isinstance(data, bytearray)

    @pytest.mark.asyncio
    async def test_with_json_dict_data(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:publish_enc",
                                            cipher=cipher_params)
        data = {'foó': 'bár'}
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc'
            raw_data = self.decrypt(self.decode(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    @pytest.mark.asyncio
    async def test_with_json_list_data(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:publish_enc",
                                            cipher=cipher_params)
        data = ['foó', 'bár']
        with mock.patch('ably.rest.rest.Http.post',
                        wraps=channel.ably.http.post) as post_mock:
            await channel.publish('event', data)
            _, kwargs = post_mock.call_args
            assert self.decode(kwargs['body'])['encoding'].strip('/') == 'json/utf-8/cipher+aes-128-cbc'
            raw_data = self.decrypt(self.decode(kwargs['body'])['data']).decode('ascii')
            assert json.loads(raw_data) == data

    @pytest.mark.asyncio
    async def test_text_utf8_decode(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:enc_stringdecode-bin",
                                            cipher=cipher_params)
        await channel.publish('event', 'foó')
        history = await channel.history()
        message = history.items[0]
        assert message.data == 'foó'
        assert isinstance(message.data, str)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_binary_type_decode(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:enc_binarydecode-bin",
                                            cipher=cipher_params)

        await channel.publish('event', bytearray(b'foob'))
        history = await channel.history()
        message = history.items[0]
        assert message.data == bytearray(b'foob')
        assert isinstance(message.data, bytearray)
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_dict_data_decode(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:enc_jsondict-bin",
                                            cipher=cipher_params)
        data = {'foó': 'bár'}
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding

    @pytest.mark.asyncio
    async def test_with_json_list_data_decode(self, msgpack_rest, cipher_params):
        channel = msgpack_rest.channels.get("persisted:enc_list-bin",
                                            cipher=cipher_params)
        data = ['foó', 'bár']
        await channel.publish('event', data)
        history = await channel.history()
        message = history.items[0]
        assert message.data == data
        assert not message.encoding
