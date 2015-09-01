class ChannelOptions(object):
    def __init__(self, encrypted=False, cipher_params=None):
        self.__encrypted = encrypted
        self.__cipher_params = cipher_params
        if encrypted and cipher_params is None:
            raise ValueError("Must set cipher_params if encrypted is True")

    @property
    def encrypted(self):
        return self.__encrypted

    @property
    def cipher_params(self):
        return self.__cipher_params
