import logging
from typing import Optional
from urllib.parse import urlencode

from ably.sync.http.http import HttpSync
from ably.sync.http.paginatedresult import PaginatedResultSync, HttpPaginatedResponseSync
from ably.sync.http.paginatedresult import format_params
from ably.sync.rest.auth import AuthSync
from ably.sync.rest.channel import ChannelsSync
from ably.sync.rest.push import PushSync
from ably.sync.util.exceptions import AblyException, catch_all
from ably.sync.types.options import Options
from ably.sync.types.stats import stats_response_processor
from ably.sync.types.tokendetails import TokenDetails

log = logging.getLogger(__name__)


class AblyRestSync:
    """Ably Rest Client"""

    def __init__(self, key: Optional[str] = None, token: Optional[str] = None,
                 token_details: Optional[TokenDetails] = None, **kwargs):
        """Create an AblyRest instance.

        :Parameters:
          **Credentials**
          - `key`: a valid key string

          **Or**
          - `token`: a valid token string
          - `token_details`: an instance of TokenDetails class

          **Optional Parameters**
          - `client_id`: Undocumented
          - `rest_host`: The host to connect to. Defaults to rest.ably.io
          - `environment`: The environment to use. Defaults to 'production'
          - `port`: The port to connect to. Defaults to 80
          - `tls_port`: The tls_port to connect to. Defaults to 443
          - `tls`: Specifies whether the client should use TLS. Defaults
            to True
          - `auth_token`: Undocumented
          - `auth_callback`: Undocumented
          - `auth_url`: Undocumented
          - `keep_alive`: use persistent connections. Defaults to True
        """
        if key is not None and ('key_name' in kwargs or 'key_secret' in kwargs):
            raise ValueError("key and key_name or key_secret are mutually exclusive. "
                             "Provider either a key or key_name & key_secret")
        if key is not None:
            options = Options(key=key, **kwargs)
        elif token is not None:
            options = Options(auth_token=token, **kwargs)
        elif token_details is not None:
            if not isinstance(token_details, TokenDetails):
                raise ValueError("token_details must be an instance of TokenDetails")
            options = Options(token_details=token_details, **kwargs)
        elif not ('auth_callback' in kwargs or 'auth_url' in kwargs or
                  # and don't have both key_name and key_secret
                  ('key_name' in kwargs and 'key_secret' in kwargs)):
            raise ValueError("key is missing. Either an API key, token, or token auth method must be provided")
        else:
            options = Options(**kwargs)

        try:
            self._is_realtime
        except AttributeError:
            self._is_realtime = False

        self.__http = HttpSync(self, options)
        self.__auth = AuthSync(self, options)
        self.__http.auth = self.__auth

        self.__channels = ChannelsSync(self)
        self.__options = options
        self.__push = PushSync(self)

    def __enter__(self):
        return self

    @catch_all
    def stats(self, direction: Optional[str] = None, start=None, end=None, params: Optional[dict] = None,
              limit: Optional[int] = None, paginated=None, unit=None, timeout=None):
        """Returns the stats for this application"""
        formatted_params = format_params(params, direction=direction, start=start, end=end, limit=limit, unit=unit)
        url = '/stats' + formatted_params
        return PaginatedResultSync.paginated_query(
            self.http, url=url, response_processor=stats_response_processor)

    @catch_all
    def time(self, timeout: Optional[float] = None) -> float:
        """Returns the current server time in ms since the unix epoch"""
        r = self.http.get('/time', skip_auth=True, timeout=timeout)
        AblyException.raise_for_response(r)
        return r.to_native()[0]

    @property
    def client_id(self) -> Optional[str]:
        return self.options.client_id

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

    @property
    def push(self):
        return self.__push

    def request(self, method: str, path: str, version: str, params:
                Optional[dict] = None, body=None, headers=None):
        if version is None:
            raise AblyException("No version parameter", 400, 40000)

        url = path
        if params:
            url += '?' + urlencode(params)

        def response_processor(response):
            items = response.to_native()
            if not items:
                return []
            if type(items) is not list:
                items = [items]
            return items

        return HttpPaginatedResponseSync.paginated_query(
            self.http, method, url, version=version, body=body, headers=headers,
            response_processor=response_processor,
            raise_on_error=False)

    def __exit__(self, *excinfo):
        self.close()

    def close(self):
        self.http.close()
