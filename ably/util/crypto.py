from __future__ import absolute_import

import logging

import six
from six.moves import range

from Crypto.Cipher import AES
from Crypto import Random

from ably.types.typedbuffer import TypedBuffer
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


class CipherParams(object):
    def __init__(self, algorithm='AES', mode='CBC', secret_key=None,
                 iv=None):
        self.__algorithm = algorithm
        self.__secret_key = secret_key
        self.__key_length = len(secret_key) * 8 if secret_key is not None else 128
        self.__mode = mode
        self.__iv = iv

    @property
    def algorithm(self):
        return self.__algorithm

    @property
    def secret_key(self):
        return self.__secret_key

    @property
    def iv(self):
        return self.__iv

    @property
    def key_length(self):
        return self.__key_length

    @property
    def mode(self):
        return self.__mode


class CbcChannelCipher(object):
    def __init__(self, cipher_params):
        self.__secret_key = (cipher_params.secret_key or
                             self.__random(cipher_params.key_length / 8))
        self.__iv = cipher_params.iv or self.__random(16)
        self.__block_size = len(self.__iv)
        if cipher_params.algorithm.lower() != 'aes':
            raise NotImplementedError('Only AES algorithm is supported')
        self.__algorithm = cipher_params.algorithm
        if cipher_params.mode.lower() != 'cbc':
            raise NotImplementedError('Only CBC mode is supported')
        self.__mode = cipher_params.mode
        self.__key_length = cipher_params.key_length
        self.__encryptor = AES.new(self.__secret_key, AES.MODE_CBC, self.__iv)

    def __pad(self, data):
        padding_size = self.__block_size - (len(data) % self.__block_size)

        padding_char = six.int2byte(padding_size)
        padded = data + padding_char * padding_size

        return padded

    def __unpad(self, data):
        padding_size = six.indexbytes(data, -1)

        if padding_size > len(data):
            # Too short
            raise AblyException('invalid-padding', 0, 0)

        if padding_size == 0:
            # Missing padding
            raise AblyException('invalid-padding', 0, 0)

        for i in range(padding_size):
            # Invalid padding bytes
            if padding_size != six.indexbytes(data, -i - 1):
                raise AblyException('invalid-padding', 0, 0)

        return data[:-padding_size]

    def __random(self, length):
        rndfile = Random.new()
        return rndfile.read(length)

    def encrypt(self, plaintext):
        padded_plaintext = self.__pad(plaintext)
        encrypted = self.__iv + self.__encryptor.encrypt(padded_plaintext)
        self.__iv = encrypted[-self.__block_size:]
        return encrypted

    def decrypt(self, ciphertext):
        iv = ciphertext[:self.__block_size]
        ciphertext = ciphertext[self.__block_size:]
        decryptor = AES.new(self.__secret_key, AES.MODE_CBC, iv)
        decrypted = decryptor.decrypt(ciphertext)
        return self.__unpad(decrypted)

    @property
    def secret_key(self):
        return self.__secret_key

    @property
    def iv(self):
        return self.__iv

    @property
    def cipher_type(self):
        return ("%s-%s-%s" % (self.__algorithm, self.__key_length,
                self.__mode)).lower()


class CipherData(TypedBuffer):
    ENCODING_ID = 'cipher'

    def __init__(self, buffer, type, cipher_type=None, **kwargs):
        self.__cipher_type = cipher_type
        super(CipherData, self).__init__(buffer, type, **kwargs)

    @property
    def encoding_str(self):
        return self.ENCODING_ID + '+' + self.__cipher_type

DEFAULT_KEYLENGTH = 16
DEFAULT_BLOCKLENGTH = 16


def get_default_params(key=None):
    rndfile = Random.new()
    key = key or rndfile.read(DEFAULT_KEYLENGTH)
    iv = rndfile.read(DEFAULT_BLOCKLENGTH)
    return CipherParams(algorithm='AES', secret_key=key, iv=iv)


def get_cipher(cipher_params):
    if cipher_params is None:
        params = get_default_params()
    elif isinstance(cipher_params, CipherParams):
        params = cipher_params
    else:
        raise AblyException("ChannelOptions not supported", 400, 40000)
    return CbcChannelCipher(params)
