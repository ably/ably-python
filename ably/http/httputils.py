from __future__ import absolute_import


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
        if binary:
            return {
                "Accept": HttpUtils.mime_types['binary']
            }
        else:
            return {
                "Accept": HttpUtils.mime_types['json']
            }

    @staticmethod
    def default_post_headers(binary=False):
        if binary:
            return {
                "Accept": HttpUtils.mime_types['binary'],
                "Content-Type": HttpUtils.mime_types['binary']
            }
        else:
            return {
                "Accept": HttpUtils.mime_types['json'],
                "Content-Type": HttpUtils.mime_types['json']
            }
