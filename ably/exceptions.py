class AblyException(BaseException):
    def __init__(self, reason, status_code, code):
        super(AblyException, self).__init__()
        self.reason = reason
        self.code = code
        self.status_code = status_code

    def __str__(self):
        return "%s %s %s" % (self.code, self.status_code, self.reason)

    @staticmethod
    def raise_for_response(response):
        if response.status_code >= 200 and response.status_code < 300:
            # Valid response
            return

        json_response = response.json()
        if json_response:
            try:
                raise AblyException(json_response['reason'], 
                    json_response['statusCode'], 
                    json_response['code'])
            except KeyError as e:
                raise AblyException("Unexpected exception decoding server response: %s" % e, 500, 50000)

        raise AblyException("", response.status_code, response.status_code*100)

    @staticmethod
    def from_exception(e):
        if isinstance(e, AblyException):
            return e
        return AblyException("Unexpected exception: %s" % e, 500, 50000)

