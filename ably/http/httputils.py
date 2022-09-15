import platform

import ably


class HttpUtils:
    default_format = "json"

    mime_types = {
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        "binary": "application/x-msgpack",
    }

    @staticmethod
    def default_get_headers(binary=False):
        headers = HttpUtils.default_headers()
        if binary:
            headers["Accept"] = HttpUtils.mime_types['binary']
        else:
            headers["Accept"] = HttpUtils.mime_types['json']
        return headers

    @staticmethod
    def default_post_headers(binary=False):
        headers = HttpUtils.default_get_headers(binary=binary)
        headers["Content-Type"] = headers["Accept"]
        return headers

    @staticmethod
    def get_host_header(host):
        return {
            'Host': host,
        }

    @staticmethod
    def default_headers():
        return {
            "X-Ably-Version": ably.api_version,
            "Ably-Agent": 'ably-python/%s python/%s' % (ably.lib_version, platform.python_version())
        }
