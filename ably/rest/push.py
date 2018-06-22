from ably.http.paginatedresult import PaginatedResult, format_params
from ably.types.device import DeviceDetails, make_device_details_response_processor

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
        """Returns a DeviceDetails object if the device id is found or results
        in a not found error if the device cannot be found.

        :Parameters:
        - `device_id`: the id of the device
        """
        path = '/push/deviceRegistrations/%s' % device_id
        response = self.ably.http.get(path)
        details = response.to_native()
        return DeviceDetails(**details)

    def list(self, **params):
        """Returns a PaginatedResult object with the list of DeviceDetails
        objects, filtered by the given parameters.

        :Parameters:
        - `**params`: the parameters used to filter the list
        """
        path = '/push/deviceRegistrations' + format_params(params)
        response_processor = make_device_details_response_processor(
            self.ably.options.use_binary_protocol)
        return PaginatedResult.paginated_query(
            self.ably.http, url=path, response_processor=response_processor)

    def save(self, device):
        """Creates or updates the device. Returns a DeviceDetails object.

        :Parameters:
        - `device`: a dictionary with the device information
        """
        device_details = DeviceDetails(**device)
        path = '/push/deviceRegistrations/%s' % device_details.id
        response = self.ably.http.put(path, body=device)
        details = response.to_native()
        return DeviceDetails(**details)
