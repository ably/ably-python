class Defaults:
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
