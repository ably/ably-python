from __future__ import absolute_import

import functools
import logging
import six

from ably.util.unicodemixin import UnicodeMixin

log = logging.getLogger(__name__)


class AblyException(BaseException, UnicodeMixin):
    def __init__(self, reason, status_code, code):
        super(AblyException, self).__init__(reason)
        self.reason = reason
        self.code = code
        self.status_code = status_code

    def __unicode__(self):
        return six.u('%s %s %s') % (self.code, self.status_code, self.reason)

    @staticmethod
    def raise_for_response(response):
        if response.status_code >= 200 and response.status_code < 300:
            # Valid response
            return

        try:
            json_response = response.json()
            if json_response:
                try:
                    raise AblyException(json_response['reason'],
                                        json_response['statusCode'],
                                        json_response['code'])
                except KeyError:
                    msg = "Unexpected exception decoding server response: %s"
                    msg = msg % response.text
                    raise AblyException(msg, 500, 50000)
        except:
            log.debug("Response: %d %s", response.status_code, response.text)
            raise AblyException(
                response.text,
                response.status_code,
                response.status_code * 100)

        raise AblyException("", response.status_code, response.status_code*100)

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
