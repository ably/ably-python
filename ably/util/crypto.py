from __future__ import absolute_import

import logging

import base64

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
        self.__algorithm = algorithm.upper()
        self.__secret_key = secret_key
        self.__key_length = len(secret_key) * 8 if secret_key is not None else 128
        self.__mode = mode.upper()
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
        if cipher_params.algorithm != 'AES':
            raise NotImplementedError('Only AES algorithm is supported')
        self.__algorithm = cipher_params.algorithm
        if cipher_params.mode != 'CBC':
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
        if isinstance(plaintext, bytearray):
            plaintext = six.binary_type(plaintext)
        padded_plaintext = self.__pad(plaintext)
        encrypted = self.__iv + self.__encryptor.encrypt(padded_plaintext)
        self.__iv = encrypted[-self.__block_size:]
        return encrypted

    def decrypt(self, ciphertext):
        if isinstance(ciphertext, bytearray):
            ciphertext = six.binary_type(ciphertext)
        iv = ciphertext[:self.__block_size]
        ciphertext = ciphertext[self.__block_size:]
        decryptor = AES.new(self.__secret_key, AES.MODE_CBC, iv)
        decrypted = decryptor.decrypt(ciphertext)
        return bytearray(self.__unpad(decrypted))

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

DEFAULT_KEYLENGTH = 256
DEFAULT_BLOCKLENGTH = 16

def generate_random_key(length=DEFAULT_KEYLENGTH):
    rndfile = Random.new()
    return rndfile.read(length // 8)

def get_default_params(params=None):
    # Backwards compatibility
    if type(params) in [six.text_type, six.binary_type]:
        log.warn("Calling get_default_params with a key directly is deprecated, it expects a params dict")
        return get_default_params({'key': params})

    key = params.get('key')
    algorithm = params.get('algorithm') or 'AES'
    iv = params.get('iv') or generate_random_key(DEFAULT_BLOCKLENGTH * 8)
    mode = params.get('mode') or 'CBC'

    if not key:
        raise ValueError("Crypto.get_default_params: a key is required")

    if type(key) == six.text_type:
        key = base64.b64decode(key)

    cipher_params = CipherParams(algorithm=algorithm, secret_key=key, iv=iv, mode=mode)
    validate_cipher_params(cipher_params)
    return cipher_params

def get_cipher(params):
    if isinstance(params, CipherParams):
        cipher_params = params
    else:
        cipher_params = get_default_params(params)
    return CbcChannelCipher(cipher_params)

def validate_cipher_params(cipher_params):
    if cipher_params.algorithm == 'AES' and cipher_params.mode == 'CBC':
        if cipher_params.key_length == 128 or cipher_params.key_length == 256:
            return
        raise ValueError('Unsupported key length ' + str(params.keyLength) + ' for aes-cbc encryption. Encryption key must be 128 or 256 bits (16 or 32 ASCII characters)')
