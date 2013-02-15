class Channel(object):
    def __init__(self, rest, name):
        self.__rest = rest
        self.__name = name

    def presence(self, params):
        raise NotImplementedError

    def history(self, params):
        raise NotImplementedError

    def publish(self, name, data):
        raise NotImplementedError


class Channels(object):
    def __init__(self, rest):
        self.__rest = rest
        self.__attached = {}

    def get(self, name):
        name = unicode(name)
        if name not in self.__attached:
            self.__attached[name] = Channel(self.rest, name)
        return self.__attached[name]

