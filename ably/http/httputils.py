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
    def default_get_headers(binary=False, variant=None):
        if variant is not None:
            lib_version = 'python.%s-%s' % (variant, ably.lib_version)
        else:
            lib_version = 'python-%s' % ably.lib_version

        headers = {
            "X-Ably-Version": ably.api_version,
            "X-Ably-Lib": lib_version,
        }
        if binary:
            headers["Accept"] = HttpUtils.mime_types['binary']
        else:
            headers["Accept"] = HttpUtils.mime_types['json']
        return headers

    @staticmethod
    def default_post_headers(binary=False, variant=None):
        headers = HttpUtils.default_get_headers(binary=binary, variant=variant)
        headers["Content-Type"] = headers["Accept"]
        return headers
