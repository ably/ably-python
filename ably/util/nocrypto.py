
class InstallPycrypto(object):
    def __getattr__(self, name):
        raise ImportError('This feature requires pycrypto')

AES = Random = InstallPycrypto()
