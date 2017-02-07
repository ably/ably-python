from __future__ import absolute_import
import random


class Defaults(object):
    protocol_version = 1
    fallback_hosts = [
        "A.ably-realtime.com",
        "B.ably-realtime.com",
        "C.ably-realtime.com",
        "D.ably-realtime.com",
        "E.ably-realtime.com",
    ]

    rest_host = "rest.ably.io"
    realtime_host = "realtime.ably.io"
    environment = 'production'

    port = 80
    tls_port = 443
    connect_timeout = 15000
    disconnect_timeout = 10000
    suspended_timeout = 60000
    comet_recv_timeout = 90000
    comet_send_timeout = 10000

    transports = []  # ["web_socket", "comet"]

    http_max_retry_count = 3

    @staticmethod
    def get_port(options):
        if options.tls:
            if options.tls_port:
                return options.tls_port
            else:
                return Defaults.tls_port
        else:
            if options.port:
                return options.port
            else:
                return Defaults.port

    @staticmethod
    def get_rest_hosts(options):
        """
        Return the list of hosts as they should be tried. First comes the main
        host. Then the fallback hosts in random order.
        The returned list will have a length of up to http_max_retry_count.
        """
        # Defaults
        host = options.rest_host
        if host is None:
            host = Defaults.rest_host

        environment = options.environment
        if environment is None:
            environment = Defaults.environment

        http_max_retry_count = options.http_max_retry_count
        if http_max_retry_count is None:
            http_max_retry_count = Defaults.http_max_retry_count

        # Prepend environment
        if environment != 'production':
            host = '%s-%s' % (environment, host)

        # Fallback hosts
        fallback_hosts = options.fallback_hosts
        if fallback_hosts is None:
            if host == Defaults.rest_host or options.fallback_hosts_use_default:
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

    @staticmethod
    def get_rest_host(options):
        return Defaults.get_rest_hosts(options)[0]

    @staticmethod
    def get_fallback_rest_hosts(options):
        return Defaults.get_rest_hosts(options)[1:]

    @staticmethod
    def get_scheme(options):
        if options.tls:
            return "https"
        else:
            return "http"
