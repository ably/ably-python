from __future__ import absolute_import

import calendar
import logging

from six.moves.urllib.parse import urlencode

from ably.http.http import Http
from ably.http.paginatedresult import PaginatedResult
from ably.rest.auth import Auth
from ably.rest.channel import Channels
from ably.transport.defaults import Defaults
from ably.util.exceptions import AblyException, catch_all
from ably.types.options import Options

from ably.types.stats import stats_response_processor

log = logging.getLogger("ably")
#logging.basicConfig(level=logging.WARNING)


class AblyRest(object):
    """Ably Rest Client"""
    def __init__(self, options=None, key=None, token=None):
        """Create an AblyRest instance.

        :Parameters:
          **Credentials**
          - `key`: a valid key string

          **Or**
          - `keyId`: Your Ably key id
          - `keyValue`: Your Ably key value

          **Optional Parameters**
          - `clientId`: Undocumented
          - `host`: The host to connect to. Defaults to rest.ably.io
          - `port`: The port to connect to. Defaults to 80
          - `tls_port`: The tls_port to connect to. Defaults to 443
          - `tls`: Specifies whether the client should use TLS. Defaults
            to True
          - `auth_token`: Undocumented
          - `auth_callback`: Undocumented
          - `auth_url`: Undocumented
          - `keep_alive`: use persistent connections. Defaults to True
        """
        hasKey = key or (options and options.keyValue and options.keyId)
        hasMeansToFetchToken = options and ( options.authUrl  or options.auth_callback)
        hasToken = token or (options and options.auth_token)
        if token and options and options.auth_token and token != options.auth_token:
            raise AblyException(reason="AblyRest token and AblyRest options token don't match. Only one needs to be set",
                                status_code=400,
                                code=40000)

        if token:
            options.auth_token = token

        if not hasKey and not hasToken and not hasMeansToFetchToken:
            raise AblyException(reason="Cannot instantiate AblyRest without a key, a token, or the means to fetch a token",
                                    status_code=400,
                                    code=40000)

        if options:
            self.__options = options
        elif key:
            self.__options = Options.with_key(key)
        elif token:
            self.__options = Options()

        self.__channels = Channels(self)    
        self.__clientId = options.clientId if options and options.clientId  else ""
        self.__http = Http(self, self.__options)
        self.__auth = Auth(self, self.__options)
        self.__http.auth = self.__auth





    @classmethod
    def with_key(cls, key):
        return cls(Options.with_key(key))

    def _format_time_param(self, t):
        try:
            return '%d' % (calendar.timegm(t.utctimetuple()) * 1000)
        except:
            return '%s' % t

    @catch_all
    def stats(self, searchParams):
        """Returns the stats for this application"""
        url = '/stats'
        return PaginatedResult.paginated_query(self.http,
                                               url, None,
                                               stats_response_processor, searchParams)

    @catch_all
    def time(self):
        """Returns the current server time in ms since the unix epoch"""
        r = self.http.get('/time', skip_auth=True, timeout=Defaults.disconnect_timeout)
        AblyException.raise_for_response(r)
        return r.json()[0]

    @property
    def clientId(self):
        return self.options.clientId

    @property
    def channels(self):
        """Returns the channels container object"""
        return self.__channels

    @property
    def auth(self):
        return self.__auth

    @property
    def http(self):
        return self.__http

    @property
    def options(self):
        return self.__options

    def setLogLevel(self,level):
      logging.basicConfig(level=level)
