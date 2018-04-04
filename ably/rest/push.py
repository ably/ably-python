
class Push(object):

    def __init__(self, ably):
        self.__ably = ably
        self.__admin = PushAdmin(ably)

    @property
    def admin(self):
        return self.__admin


class PushAdmin(object):

    def __init__(self, ably):
        self.__ably = ably

    @property
    def ably(self):
        return self.__ably

    def publish(self, recipient, data):
        if not isinstance(recipient, dict):
            raise TypeError('Unexpected %s recipient, expected a dict' % type(recipient))

        if not isinstance(data, dict):
            raise TypeError('Unexpected %s data, expected a dict' % type(recipient))

        if not recipient:
            raise ValueError('recipient is empty')

        if not data:
            raise ValueError('data is empty')

        body = data.copy()
        body.update({'recipient': recipient})
        return self.ably.http.post('/push/publish', body=body)
