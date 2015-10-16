
import base64

import six

import hashlib
import hmac


class TokenRequest(object):

    def __init__(self, key_name=None, client_id=None, nonce=None, mac=None,
                 capability=None, ttl=None, timestamp=None):
        self.__key_name = key_name
        self.__client_id = client_id
        self.__nonce = nonce
        self.__mac = mac
        self.__capability = capability
        self.__ttl = ttl
        self.__timestamp = timestamp

    def sign_request(self, key_secret):
        sign_text = six.u("\n").join([six.text_type(x) for x in [
            self.key_name or "",
            self.ttl or "",
            self.capability or "",
            self.client_id or "",
            "%d" % (self.timestamp or 0),
            self.nonce or "",
            "",  # to get the trailing new line
        ]])
        try:
            key_secret = key_secret.encode('utf8')
        except AttributeError:
            pass
        try:
            sign_text = sign_text.encode('utf8')
        except AttributeError:
            pass
        mac = hmac.new(key_secret, sign_text, hashlib.sha256).digest()
        self.mac = base64.b64encode(mac).decode('utf8')

    def to_dict(self):
        return {
            'keyName': self.key_name,
            'clientId': self.client_id,
            'ttl': self.ttl,
            'nonce': self.nonce,
            'capability': self.capability,
            'timestamp': self.timestamp,
            'mac': self.mac
        }

    @property
    def key_name(self):
        return self.__key_name

    @property
    def client_id(self):
        return self.__client_id

    @property
    def nonce(self):
        return self.__nonce

    @property
    def mac(self):
        return self.__mac

    @mac.setter
    def mac(self, mac):
        self.__mac = mac

    @property
    def capability(self):
        return self.__capability

    @property
    def ttl(self):
        return self.__ttl

    @property
    def timestamp(self):
        return self.__timestamp
