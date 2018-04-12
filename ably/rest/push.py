from ably.types.device import DeviceDetails

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
        self.__device_registrations = PushDeviceRegistrations(ably)

    @property
    def ably(self):
        return self.__ably

    @property
    def device_registrations(self):
        return self.__device_registrations

    def publish(self, recipient, data, timeout=None):
        """Publish a push notification to a single device.

        :Parameters:
        - `recipient`: the recipient of the notification
        - `data`: the data of the notification
        """
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
        return self.ably.http.post('/push/publish', body=body, timeout=timeout)


class PushDeviceRegistrations(object):

    def __init__(self, ably):
        self.__ably = ably

    @property
    def ably(self):
        return self.__ably

    def get(self, device_id):
        path = '/push/deviceRegistrations/%s' % device_id
        response = self.ably.http.get(path)
        details = response.to_native()
        return DeviceDetails(**details)

    def save(self, device):
        device_details = DeviceDetails(**device)
        path = '/push/deviceRegistrations/%s' % device_details.id
        response = self.ably.http.put(path, body=device)
        details = response.to_native()
        return DeviceDetails(**details)
