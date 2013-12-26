class ResourceCount(object):
    def __init__(self, opened=0.0, peak=0.0, mean=0.0, min=0.0, refused=0.0):
        self.opened = opened
        self.peak = peak
        self.mean = mean
        self.min = min
        self.refused = refused


class ConnectionTypes(object):
    def __init__(self):
        self.all = ResourceCount()
        self.plain = ResourceCount()
        self.tls = ResourceCount()


class MessageCount(object):
    def __init__(self, count=0.0, data=0.0):
        self.count = count
        self.data = data


class MessageTypes(object):
    def __init__(self, all=None, messages=None, presence=None):
        self.all = all or MessageCount()
        self.messages = messages or MessageCount()
        self.presence = presence or MessageCount()


class MessageTraffic(object):
    def __init__(self, all=None, realtime=None, rest=None, push=None, http_stream=None):
        self.all = all or MessageTypes()
        self.realtime = realtime or MessageTypes()
        self.rest = rest or MessageTypes()
        self.push = push or MessageTypes()
        self.http_stream = http_stream or MessageTypes()


class RequestCount(object):
    def __init__(self, succeeded=0.0, failed=0.0, refused=0.0):
        self.succeeded = succeeded
        self.failed = failed
        self.refused = refused


class Stats(object):
    def __init__(self, all=None, inbound=None, outbound=None, persisted=None, connections=None, channels=None, api_requests=None, token_requests=None):
        self.all = all or MessageTypes()
        self.inbound = inbound or MessageTraffic()
        self.outbound = outbound or MessageTraffic()
        self.persisted = persisted or MessageTypes()
        self.connections = connections or ConnectionTypes()
        self.channels = channels or ResourceCount()
        self.api_requests = api_requests or RequestCount()
        self.token_requests = token_requests or RequestCount()
