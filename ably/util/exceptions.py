import functools
import logging


log = logging.getLogger(__name__)


class AblyException(Exception):
    def __new__(cls, message, status_code, code):
        if cls == AblyException and status_code == 401:
            return AblyAuthException(message, status_code, code)
        return super().__new__(cls, message, status_code, code)

    def __init__(self, message, status_code, code):
        super().__init__()
        self.message = message
        self.code = code
        self.status_code = status_code

    def __str__(self):
        return '%s %s %s' % (self.code, self.status_code, self.message)

    @property
    def is_server_error(self):
        return 500 <= self.status_code <= 599

    @staticmethod
    def raise_for_response(response):
        if response.status_code >= 200 and response.status_code < 300:
            # Valid response
            return

        try:
            json_response = response.json()
        except Exception:
            log.debug("Response not json: %d %s",
                      response.status_code,
                      response.text)
            raise AblyException(message=response.text,
                                status_code=response.status_code,
                                code=response.status_code * 100)

        if json_response and 'error' in json_response:
            error = json_response['error']
            try:
                raise AblyException(
                    message=error['message'],
                    status_code=error['statusCode'],
                    code=int(error['code']),
                )
            except KeyError:
                msg = "Unexpected exception decoding server response: %s"
                msg = msg % response.text
                raise AblyException(message=msg, status_code=500, code=50000)

        raise AblyException(message="",
                            status_code=response.status_code,
                            code=response.status_code * 100)

    @staticmethod
    def from_exception(e):
        if isinstance(e, AblyException):
            return e
        return AblyException("Unexpected exception: %s" % e, 500, 50000)


def catch_all(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.exception(e)
            raise AblyException.from_exception(e)

    return wrapper


class AblyAuthException(AblyException):
    pass


class IncompatibleClientIdException(AblyException):
    pass
