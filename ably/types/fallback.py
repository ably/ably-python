from __future__ import absolute_import

from random import randint

from ably.transport.defaults import Defaults
import logging
log = logging.getLogger(__name__)


class Fallback(object):
    def __init__(self, hosts):
      self.__hosts = hosts or []


    def random_host(self):
        length = len(self.__hosts)
        if length > 0:
            index = randint(0,length -1)
            host = self.__hosts.pop(index)
            return host
        else:
            return None


    def should_try_fallback(self, options, response):
        #fallback only attempted if restHost is the default restHost
        if not options.restHost == Defaults.restHost:
            return False

        fallback_codes = set([500, 501, 502, 503,504])
        if response and response.error and  response.error.statusCode in fallback_codes:
            return True
        return False
            






