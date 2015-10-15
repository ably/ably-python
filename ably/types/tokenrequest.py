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

    @property
    def capability(self):
        return self.__capability

    @property
    def ttl(self):
        return self.__ttl

    @property
    def timestamp(self):
        return self.__timestamp
