class HttpUtils(object):
    default_format = "json"

    mime_types = {
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        #"binary": "application/x-thrift",
    }

    @staticmethod
    def default_get_headers(binary=False):
        if binary:
            raise AblyException()
        else:
            return {
                "Accept": "application/json",
            }

    @staticmethod
    def default_post_headers(binary=False):
        if binary:
            raise AblyException()
        else:
            return {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
