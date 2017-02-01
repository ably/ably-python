from __future__ import absolute_import

import ably


class HttpUtils(object):
    default_format = "json"

    mime_types = {
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        "binary": "application/x-msgpack",
    }

    @staticmethod
    def default_get_headers(binary=False):
        headers = {
            "X-Ably-Version": ably.api_version,
            "X-Ably-Lib": 'python-%s' % ably.lib_version,
        }
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
