import logging
from typing import Optional
from ably.util.exceptions import catch_all
from ably.types.tokendetails import TokenDetails
from ably.rest.rest import AblyRest

log = logging.getLogger(__name__)


class AblyRestSync(AblyRest):
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
        super().__init__(key, token, token_details, **kwargs)

    def __enter__(self):
        return self

    @catch_all
    def stats(self, direction: Optional[str] = None, start=None, end=None, params: Optional[dict] = None,
                    limit: Optional[int] = None, paginated=None, unit=None, timeout=None):
        """Returns the stats for this application"""
        return super().stats(direction, start, end, params, limit, paginated, unit, timeout)

    @catch_all
    def time(self, timeout: Optional[float] = None) -> float:
        """Returns the current server time in ms since the unix epoch"""
        return super().time(timeout)

    async def request(self, method: str, path: str, version: str, params:
                      Optional[dict] = None, body=None, headers=None):
        return super().request(method, path, version, params, body, headers)

    def __exit__(self, *excinfo):
        self.close()

    def close(self):
        super().close()
