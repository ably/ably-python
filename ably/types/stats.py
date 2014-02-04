from __future__ import absolute_import

class ResourceCount(object):
    def __init__(self, opened=0.0, peak=0.0, mean=0.0, min=0.0, refused=0.0):
        self.opened = opened
        self.peak = peak
        self.mean = mean
        self.min = min
        self.refused = refused

    @staticmethod
    def from_dict(rc_dict):
        rc_dict = rc_dict or {}
        kwargs = {
            "opened": rc_dict.get("opened"),
            "peak": rc_dict.get("peak"),
            "mean": rc_dict.get("mean"),
            "min": rc_dict.get("min"),
            "refused": rc_dict.get("refused"),
        }

class ConnectionTypes(object):
    def __init__(self):
        self.all = ResourceCount()
        self.plain = ResourceCount()
        self.tls = ResourceCount()

    @staticmethod
    def from_dict(ct_dict):
        ct_dict = ct_dict or {}
        kwargs = {
            "all": ct_dict.get("all"),
            "plain": ct_dict.get("plain"),
            "tls": ct_dict.get("tls"),
        }
        return ConnectionTypes(**kwargs)


class MessageCount(object):
    def __init__(self, count=0.0, data=0.0):
        self.count = count
        self.data = data

    @staticmethod
    def from_dict(mc_dict):
        mc_dict = mc_dict or {}
        kwargs = {
            "count": mc_dict.get("count"),
            "data": mc_dict.get("data"),
        }
        return MessageCount(**kwargs)


class MessageTypes(object):
    def __init__(self, all=None, messages=None, presence=None):
        self.all = all or MessageCount()
        self.messages = messages or MessageCount()
        self.presence = presence or MessageCount()

    @staticmethod
    def from_dict(mt_dict):
        mt_dict = mt_dict or {}
        kwargs = {
            "all": mt_dict.get("all"),
            "messages": mt_dict.get("messages"),
            "presence": mt_dict.get("presence"),
        }
        return MessageTypes(**kwargs)


class MessageTraffic(object):
    def __init__(self, all=None, realtime=None, rest=None, push=None, http_stream=None):
        self.all = all or MessageTypes()
        self.realtime = realtime or MessageTypes()
        self.rest = rest or MessageTypes()
        self.push = push or MessageTypes()
        self.http_stream = http_stream or MessageTypes()

    @staticmethod
    def from_dict(mt_dict):
        mt_dict = mt_dict or {}
        kwargs = {
            "all": mt_dict.get("all"),
            "realtime": mt_dict.get("realtime"),
            "rest": mt_dict.get("rest"),
            "push": mt_dict.get("push"),
            "http_stream": mt_dict.get("httpStream"),
        }
        return MessageTraffic(**kwargs)


class RequestCount(object):
    def __init__(self, succeeded=0.0, failed=0.0, refused=0.0):
        self.succeeded = succeeded
        self.failed = failed
        self.refused = refused

    @staticmethod
    def from_dict(rc_dict):
        rc_dict = rc_dict or {}
        kwargs = {
                "succeeded": rc_dict.get("succeeded"),
                "failed": rc_dict.get("failed"),
                "refused": rc_dict.get("refused"),
        }
        return RequestCount(**kwargs)


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

    @staticmethod
    def from_dict(stats_dict):
        stats_dict = stats_dict or {}

        kwargs = {
            "all": MessageTypes.from_dict(stats_dict.get("all")),
            "inbound": MessageTraffic.from_dict(stats_dict.get("inbound")),
            "outbound": MessageTraffic.from_dict(stats_dict.get("outbound")),
            "persisted": MessageTypes.from_dict(stats_dict.get("persisted")),
            "connections": ConnectionTypes.from_dict(stats_dict.get("connections")),
            "channels": ResourceCount.from_dict(stats_dict["channels"]),
            "api_requests": RequestCount.from_dict(stats_dict["apiRequests"]),
            "token_requests": RequestCount.from_dict(stats_dict["tokenRequests"]),
        }

        return Stats(**kwargs)

    @staticmethod
    def from_array(stats_array):
        return [Stats.from_dict(d) for d in stats_array]

def stats_response_processor(response):
    stats_array = response.json()

    return Stats.from_array(stats_array)
