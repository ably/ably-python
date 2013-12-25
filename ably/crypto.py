import six
from Crypto.Cipher import AES

class CbcChannelCipher(object):
    def __init__(self, algorithm="AES", secret_key=None, iv=None):
        self.__algorithm = algorithm
        self.__block_size = len(iv)
        self.__secret_key = secret_key
        self.__iv = iv
        self.__encryptor = AES.new(self.__secret_key, AES.MODE_CBC, iv)

    def __pad(self, data):
        padding_size = self.__block_size - (len(data) % self.__block_size)

        padding_char = bytes([padding_size]) if six.PY3 else chr(padding_size)
        return data + padding_char * padding_size

    def __unpad(self, data):
        padding_size = data[-1] if six.PY3 else ord(data[-1])
        return data[:-padding_size]

    def encrypt(self, plaintext):
        padded_plaintext = self.__pad(plaintext)
        encrypted = self.__iv + self.__encryptor.encrypt(padded_plaintext)
        self.__iv = encrypted[-self.__block_size:]
        return encrypted
        

    def decrypt(self, ciphertext):
        iv = ciphertext[:self.__block_size]
        ciphertext = ciphertext[self.__block_size:]
        decryptor = AES.new(self.__secret_key, AES.MODE_CBC, iv)
        return self.__unpad(decryptor.decrypt(ciphertext))
