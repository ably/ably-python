from __future__ import absolute_import

from ably.util.exceptions import AblyException


class HttpUtils(object):
    default_format = "json"

    mime_types = {
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        # "binary": "application/x-thrift",
    }

    @staticmethod
    def default_get_headers(binary=False):
        if binary:
            raise AblyException(reason="Binary protocol is not implemented",
                                status_code=400,
                                code=40000)
        else:
            return {
                "Accept": "application/json",
            }

    @staticmethod
    def default_post_headers(binary=False):
        if binary:
            raise AblyException(reason="Binary protocol is not implemented",
                                status_code=400,
                                code=40000)
        else:
            return {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
