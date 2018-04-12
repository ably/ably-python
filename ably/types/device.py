
class DeviceDetails(object):

    def __init__(self, id, clientId=None, formFactor=None, metadata=None,
                 platform=None, push=None, updateToken=None,
                 deviceSecret=None, appId=None):
        self.__id = id
        self.__client_id = clientId
        self.__form_factor = formFactor
        self.__metadata = metadata
        self.__platform = platform
        self.__push = push
        self.__update_token = updateToken
        self.__device_secret = deviceSecret
        self.__app_id = appId

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
    def device_secret(self):
        return self.__device_secret

    @property
    def app_id(self):
        return self.__app_id
