import logging
from datetime import datetime

log = logging.getLogger(__name__)


class ResourceCount:
    def __init__(self, opened=0, peak=0, mean=0, min=0, refused=0):
        self.opened = opened
        self.peak = peak
        self.mean = mean
        self.min = min
        self.refused = refused

    @staticmethod
    def from_dict(rc_dict):
        rc_dict = rc_dict or {}
        expected = ['opened', 'peak', 'mean', 'min', 'refused']
        kwargs = {k: rc_dict[k] for k in rc_dict if (k in expected)}

        return ResourceCount(**kwargs)


class ConnectionTypes:
    def __init__(self, all=None, plain=None, tls=None):
        self.all = all or ResourceCount()
        self.plain = plain or ResourceCount()
        self.tls = tls or ResourceCount()

    @staticmethod
    def from_dict(ct_dict):
        ct_dict = ct_dict or {}
        kwargs = {
            "all": ResourceCount.from_dict(ct_dict.get("all")),
            "plain": ResourceCount.from_dict(ct_dict.get("plain")),
            "tls": ResourceCount.from_dict(ct_dict.get("tls")),
        }
        return ConnectionTypes(**kwargs)


class MessageCount:
    def __init__(self, count=0, data=0):
        self.count = count
        self.data = data

    @staticmethod
    def from_dict(mc_dict):
        mc_dict = mc_dict or {}
        expected = ['count', 'data']
        kwargs = {k: mc_dict[k] for k in mc_dict if (k in expected)}
        return MessageCount(**kwargs)


class MessageTypes:
    def __init__(self, all=None, messages=None, presence=None):
        self.all = all or MessageCount()
        self.messages = messages or MessageCount()
        self.presence = presence or MessageCount()

    @staticmethod
    def from_dict(mt_dict):
        mt_dict = mt_dict or {}
        kwargs = {
            "all": MessageCount.from_dict(mt_dict.get("all")),
            "messages": MessageCount.from_dict(mt_dict.get("messages")),
            "presence": MessageCount.from_dict(mt_dict.get("presence")),
        }
        return MessageTypes(**kwargs)


class MessageTraffic:
    def __init__(self, all=None, realtime=None, rest=None, webhook=None):
        self.all = all or MessageTypes()
        self.realtime = realtime or MessageTypes()
        self.rest = rest or MessageTypes()
        self.webhook = webhook or MessageTypes()

    @staticmethod
    def from_dict(mt_dict):
        mt_dict = mt_dict or {}
        kwargs = {
            "all": MessageTypes.from_dict(mt_dict.get("all")),
            "realtime": MessageTypes.from_dict(mt_dict.get("realtime")),
            "rest": MessageTypes.from_dict(mt_dict.get("rest")),
            "webhook": MessageTypes.from_dict(mt_dict.get("webhook")),
        }
        return MessageTraffic(**kwargs)


class RequestCount:
    def __init__(self, succeeded=0, failed=0, refused=0):
        self.succeeded = succeeded
        self.failed = failed
        self.refused = refused

    @staticmethod
    def from_dict(rc_dict):
        rc_dict = rc_dict or {}
        expected = ['succeeded', 'failed', 'refused']
        kwargs = {k: rc_dict[k] for k in rc_dict if (k in expected)}
        return RequestCount(**kwargs)


class Stats:

    def __init__(self, all=None, inbound=None, outbound=None, persisted=None,
                 connections=None, channels=None, api_requests=None,
                 token_requests=None, interval_granularity=None,
                 interval_id=None):
        self.all = all or MessageTypes()
        self.inbound = inbound or MessageTraffic()
        self.outbound = outbound or MessageTraffic()
        self.persisted = persisted or MessageTypes()
        self.connections = connections or ConnectionTypes()
        self.channels = channels or ResourceCount()
        self.api_requests = api_requests or RequestCount()
        self.token_requests = token_requests or RequestCount()
        self.interval_id = interval_id or ''
        self.interval_granularity = (interval_granularity or
                                     granularity_from_interval_id(self.interval_id))
        self.interval_time = interval_from_interval_id(self.interval_id)

    @classmethod
    def from_dict(cls, stats_dict):
        stats_dict = stats_dict or {}

        kwargs = {
            "all": MessageTypes.from_dict(stats_dict.get("all")),
            "inbound": MessageTraffic.from_dict(stats_dict.get("inbound")),
            "outbound": MessageTraffic.from_dict(stats_dict.get("outbound")),
            "persisted": MessageTypes.from_dict(stats_dict.get("persisted")),
            "connections": ConnectionTypes.from_dict(stats_dict.get("connections")),
            "channels": ResourceCount.from_dict(stats_dict.get("channels")),
            "api_requests": RequestCount.from_dict(stats_dict.get("apiRequests")),
            "token_requests": RequestCount.from_dict(stats_dict.get("tokenRequests")),
            "interval_granularity": stats_dict.get("unit"),
            "interval_id": stats_dict.get("intervalId")
        }

        return cls(**kwargs)

    @classmethod
    def from_array(cls, stats_array):
        return [cls.from_dict(d) for d in stats_array]

    @staticmethod
    def to_interval_id(date_time, granularity):
        return date_time.strftime(INTERVALS_FMT[granularity])


def stats_response_processor(response):
    stats_array = response.to_native()
    return Stats.from_array(stats_array)


INTERVALS_FMT = {
    'minute': '%Y-%m-%d:%H:%M',
    'hour': '%Y-%m-%d:%H',
    'day': '%Y-%m-%d',
    'month': '%Y-%m',
}


def granularity_from_interval_id(interval_id):
    for key, value in INTERVALS_FMT.items():
        try:
            datetime.strptime(interval_id, value)
            return key
        except ValueError:
            pass
    raise ValueError("Unsuported intervalId")


def interval_from_interval_id(interval_id):
    granularity = granularity_from_interval_id(interval_id)
    return datetime.strptime(interval_id, INTERVALS_FMT[granularity])
