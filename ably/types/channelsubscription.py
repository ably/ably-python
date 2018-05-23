from .utils import camel_to_snake, snake_to_camel


class PushChannelSubscription(object):

    def __init__(self, channel, device_id=None, client_id=None, app_id=None):
        if not device_id and not client_id:
            raise ValueError('missing expected device or client id')

        if device_id and client_id:
            raise ValueError('both device and client id given, only one expected')

        self.__channel = channel
        self.__device_id = device_id
        self.__client_id = client_id
        self.__app_id = app_id

    @property
    def channel(self):
        return self.__channel

    @property
    def device_id(self):
        return self.__device_id

    @property
    def client_id(self):
        return self.__client_id

    @property
    def app_id(self):
        return self.__app_id

    def as_dict(self):
        keys = ['channel', 'device_id', 'client_id', 'app_id']
        obj = {snake_to_camel(key): getattr(self, key) for key in keys}
        return obj

    @classmethod
    def from_dict(self, obj):
        obj = {camel_to_snake(key): value for key, value in obj.items()}
        return self(**obj)

    @classmethod
    def factory(self, subscription):
        if isinstance(subscription, self):
            return subscription

        return self.from_dict(subscription)
