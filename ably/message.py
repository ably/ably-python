import base64

def decode_data(m):
    encoding = m.get("encoding", "")
    if "cipher+base64" == encoding:
        raise "not-yet-implemented"
    elif "base64" == encoding:
        return base64.b64decode(m.get("data", u""))
    else:
        return m.get("data", "")


class Message(object):
    def __init__(self, data):
        self.__timestamp = data.get("timestamp", 0)
        self.__name = data.get("name", "")
        self.__data = decode_data(data)

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def name(self):
        return self.__name

    @property
    def data(self):
        return self.__data
