class Defaults:
    protocol_version = "2"
    fallback_hosts = [
        "a.ably-realtime.com",
        "b.ably-realtime.com",
        "c.ably-realtime.com",
        "d.ably-realtime.com",
        "e.ably-realtime.com",
    ]

    rest_host = "rest.ably.io"
    realtime_host = "realtime.ably.io"  # RTN2
    connectivity_check_url = "https://internet-up.ably-realtime.com/is-the-internet-up.txt"
    environment = 'production'

    port = 80
    tls_port = 443
    connect_timeout = 15000
    disconnect_timeout = 10000
    suspended_timeout = 60000
    comet_recv_timeout = 90000
    comet_send_timeout = 10000
    realtime_request_timeout = 10000
    channel_retry_timeout = 15000
    disconnected_retry_timeout = 15000
    connection_state_ttl = 120000
    suspended_retry_timeout = 30000

    transports = []  # ["web_socket", "comet"]

    http_max_retry_count = 3

    fallback_retry_timeout = 600000  # 10min

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
    def get_scheme(options):
        if options.tls:
            return "https"
        else:
            return "http"

    @staticmethod
    def get_environment_fallback_hosts(environment):
        return [
            environment + "-a-fallback.ably-realtime.com",
            environment + "-b-fallback.ably-realtime.com",
            environment + "-c-fallback.ably-realtime.com",
            environment + "-d-fallback.ably-realtime.com",
            environment + "-e-fallback.ably-realtime.com",
        ]
