import random

from ably.transport.defaults import Defaults
from ably.types.authoptions import AuthOptions


class Options(AuthOptions):
    def __init__(self, client_id=None, log_level=0, tls=True, rest_host=None,
                 realtime_host=None, port=0, tls_port=0, use_binary_protocol=True,
                 queue_messages=False, recover=False, environment=None,
                 http_open_timeout=None, http_request_timeout=None,
                 http_max_retry_count=None, http_max_retry_duration=None,
                 fallback_hosts=None, fallback_hosts_use_default=None, fallback_retry_timeout=None,
                 idempotent_rest_publishing=None,
                 **kwargs):
        super().__init__(**kwargs)

        # TODO check these defaults
        if fallback_retry_timeout is None:
            fallback_retry_timeout = Defaults.fallback_retry_timeout

        if environment is not None and rest_host is not None:
            raise ValueError('specify rest_host or environment, not both')

        if idempotent_rest_publishing is None:
            from ably import api_version
            idempotent_rest_publishing = api_version >= '1.2'

        self.__client_id = client_id
        self.__log_level = log_level
        self.__tls = tls
        self.__rest_host = rest_host
        self.__realtime_host = realtime_host
        self.__port = port
        self.__tls_port = tls_port
        self.__use_binary_protocol = use_binary_protocol
        self.__queue_messages = queue_messages
        self.__recover = recover
        self.__environment = environment
        self.__http_open_timeout = http_open_timeout
        self.__http_request_timeout = http_request_timeout
        self.__http_max_retry_count = http_max_retry_count
        self.__http_max_retry_duration = http_max_retry_duration
        self.__fallback_hosts = fallback_hosts
        self.__fallback_hosts_use_default = fallback_hosts_use_default
        self.__fallback_retry_timeout = fallback_retry_timeout
        self.__idempotent_rest_publishing = idempotent_rest_publishing

        self.__rest_hosts = self.__get_rest_hosts()

    @property
    def client_id(self):
        return self.__client_id

    @client_id.setter
    def client_id(self, value):
        self.__client_id = value

    @property
    def log_level(self):
        return self.__log_level

    @log_level.setter
    def log_level(self, value):
        self.__log_level = value

    @property
    def tls(self):
        return self.__tls

    @tls.setter
    def tls(self, value):
        self.__tls = value

    @property
    def rest_host(self):
        return self.__rest_host

    @rest_host.setter
    def rest_host(self, value):
        self.__rest_host = value

    @property
    def realtime_host(self):
        return self.__realtime_host

    @realtime_host.setter
    def realtime_host(self, value):
        self.__realtime_host = value

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, value):
        self.__port = value

    @property
    def tls_port(self):
        return self.__tls_port

    @tls_port.setter
    def tls_port(self, value):
        self.__tls_port = value

    @property
    def use_binary_protocol(self):
        return self.__use_binary_protocol

    @use_binary_protocol.setter
    def use_binary_protocol(self, value):
        self.__use_binary_protocol = value

    @property
    def queue_messages(self):
        return self.__queue_messages

    @queue_messages.setter
    def queue_messages(self, value):
        self.__queue_messages = value

    @property
    def recover(self):
        return self.__recover

    @recover.setter
    def recover(self, value):
        self.__recover = value

    @property
    def environment(self):
        return self.__environment

    @property
    def http_open_timeout(self):
        return self.__http_open_timeout

    @http_open_timeout.setter
    def http_open_timeout(self, value):
        self.__http_open_timeout = value

    @property
    def http_request_timeout(self):
        return self.__http_request_timeout

    @http_request_timeout.setter
    def http_request_timeout(self, value):
        self.__http_request_timeout = value

    @property
    def http_max_retry_count(self):
        return self.__http_max_retry_count

    @http_max_retry_count.setter
    def http_max_retry_count(self, value):
        self.__http_max_retry_count = value

    @property
    def http_max_retry_duration(self):
        return self.__http_max_retry_duration

    @http_max_retry_duration.setter
    def http_max_retry_duration(self, value):
        self.__http_max_retry_duration = value

    @property
    def fallback_hosts(self):
        return self.__fallback_hosts

    @property
    def fallback_hosts_use_default(self):
        return self.__fallback_hosts_use_default

    @property
    def fallback_retry_timeout(self):
        return self.__fallback_retry_timeout

    @property
    def idempotent_rest_publishing(self):
        return self.__idempotent_rest_publishing

    def __get_rest_hosts(self):
        """
        Return the list of hosts as they should be tried. First comes the main
        host. Then the fallback hosts in random order.
        The returned list will have a length of up to http_max_retry_count.
        """
        # Defaults
        host = self.rest_host
        if host is None:
            host = Defaults.rest_host

        environment = self.environment
        if environment is None:
            environment = Defaults.environment

        http_max_retry_count = self.http_max_retry_count
        if http_max_retry_count is None:
            http_max_retry_count = Defaults.http_max_retry_count

        # Prepend environment
        if environment != 'production':
            host = '%s-%s' % (environment, host)

        # Fallback hosts
        fallback_hosts = self.fallback_hosts
        if fallback_hosts is None:
            if host == Defaults.rest_host or self.fallback_hosts_use_default:
                fallback_hosts = Defaults.fallback_hosts
            else:
                fallback_hosts = []

        # Shuffle
        fallback_hosts = list(fallback_hosts)
        random.shuffle(fallback_hosts)

        # First main host
        hosts = [host] + fallback_hosts
        hosts = hosts[:http_max_retry_count]
        return hosts

    def get_rest_hosts(self):
        return self.__rest_hosts

    def get_rest_host(self):
        return self.__rest_hosts[0]

    def get_fallback_rest_hosts(self):
        return self.__rest_hosts[1:]
