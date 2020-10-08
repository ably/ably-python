import base64
import json
import logging

from ably.util.crypto import CipherData


log = logging.getLogger(__name__)


class EncodeDataMixin:

    def __init__(self, encoding):
        self.encoding = encoding

    @property
    def encoding(self):
        return '/'.join(self._encoding_array).strip('/')

    @encoding.setter
    def encoding(self, encoding):
        if not encoding:
            self._encoding_array = []
        else:
            self._encoding_array = encoding.strip('/').split('/')

    @staticmethod
    def decode(data, encoding='', cipher=None):
        encoding = encoding.strip('/')
        encoding_list = encoding.split('/')

        while encoding_list:
            encoding = encoding_list.pop()
            if not encoding:
                # With messagepack, binary data is sent as bytes, without need
                # to specify the base64 encoding. Here we coerce to bytearray,
                # since that's what is used with the Json transport; though it
                # can be argued that it should be the other way, and use always
                # bytes, never bytearray.
                if type(data) is bytes:
                    data = bytearray(data)
                continue
            if encoding == 'json':
                if isinstance(data, bytes):
                    data = data.decode()
                if isinstance(data, list) or isinstance(data, dict):
                    continue
                data = json.loads(data)
            elif encoding == 'base64' and isinstance(data, bytes):
                data = bytearray(base64.b64decode(data))
            elif encoding == 'base64':
                data = bytearray(base64.b64decode(data.encode('utf-8')))
            elif encoding.startswith('%s+' % CipherData.ENCODING_ID):
                if not cipher:
                    log.error('Message cannot be decrypted as the channel is '
                              'not set up for encryption & decryption')
                    encoding_list.append(encoding)
                    break
                data = cipher.decrypt(data)
            elif encoding == 'utf-8' and isinstance(data, (bytes, bytearray)):
                data = data.decode('utf-8')
            elif encoding == 'utf-8':
                pass
            else:
                log.error('Message cannot be decoded. '
                          "Unsupported encoding type: '%s'" % encoding)
                encoding_list.append(encoding)
                break

        encoding = '/'.join(encoding_list)
        return {'encoding': encoding, 'data': data}

    @classmethod
    def from_encoded_array(cls, objs, cipher=None):
        return [cls.from_encoded(obj, cipher=cipher) for obj in objs]
