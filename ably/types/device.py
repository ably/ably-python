DevicePushTransportType = {'fcm', 'gcm', 'apns', 'web'}
DevicePlatform = {'android', 'ios', 'browser'}
DeviceFormFactor = {'phone', 'tablet', 'desktop', 'tv', 'watch', 'car', 'embedded', 'other'}


class DeviceDetails(object):

    def __init__(self, id, clientId=None, formFactor=None, metadata=None,
                 platform=None, push=None, updateToken=None, appId=None,
                 deviceIdentityToken=None):

        if push:
            recipient = push.get('recipient')
            if recipient:
                transport_type = recipient.get('transportType')
                if transport_type is not None and transport_type not in DevicePushTransportType:
                    raise ValueError('unexpected transport type {}'.format(transport_type))

        if platform is not None and platform not in DevicePlatform:
            raise ValueError('unexpected platform {}'.format(platform))

        if formFactor is not None and formFactor not in DeviceFormFactor:
            raise ValueError('unexpected form factor {}'.format(formFactor))

        self.__id = id
        self.__client_id = clientId
        self.__form_factor = formFactor
        self.__metadata = metadata
        self.__platform = platform
        self.__push = push
        self.__update_token = updateToken
        self.__app_id = appId
        self.__device_identity_token = deviceIdentityToken

    @property
    def id(self):
        return self.__id

    @property
    def client_id(self):
        return self.__client_id

    @property
    def form_factor(self):
        return self.__form_factor

    @property
    def metadata(self):
        return self.__metadata

    @property
    def platform(self):
        return self.__platform

    @property
    def push(self):
        return self.__push

    @property
    def update_token(self):
        return self.__update_token

    @property
    def app_id(self):
        return self.__app_id

    @property
    def device_identity_token(self):
        return self.__device_identity_token

    @classmethod
    def from_array(cls, array):
        return [cls.from_dict(d) for d in array]

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def make_device_details_response_processor(binary):
    def device_details_response_processor(response):
        native = response.to_native()
        return DeviceDetails.from_array(native)
    return device_details_response_processor
