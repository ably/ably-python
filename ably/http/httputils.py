import base64
import os
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
    def default_get_headers(binary=False, version=None):
        headers = HttpUtils.default_headers(version=version)
        if binary:
            headers["Accept"] = HttpUtils.mime_types['binary']
        else:
            headers["Accept"] = HttpUtils.mime_types['json']
        return headers

    @staticmethod
    def default_post_headers(binary=False, version=None):
        headers = HttpUtils.default_get_headers(binary=binary, version=version)
        headers["Content-Type"] = headers["Accept"]
        return headers

    @staticmethod
    def get_host_header(host):
        return {
            'Host': host,
        }

    @staticmethod
    def default_headers(version=None):
        if version is None:
            version = ably.api_version
        return {
            "X-Ably-Version": version,
            "Ably-Agent": 'ably-python/%s python/%s' % (ably.lib_version, platform.python_version())
        }

    @staticmethod
    def get_query_params(options):
        params = {}

        if options.add_request_ids:
            params['request_id'] = base64.urlsafe_b64encode(os.urandom(12)).decode('ascii')

        return params
