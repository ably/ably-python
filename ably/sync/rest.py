import logging
from typing import Optional

from ably.executer.decorator import force_sync, close_app_eventloop
from ably.sync.auth import AuthSync
from ably.sync.channel import ChannelsSync
from ably.sync.http import HttpSync
from ably.types.tokendetails import TokenDetails
from ably.util.exceptions import catch_all
from ably.rest.rest import AblyRest

log = logging.getLogger(__name__)


class AblyRestSync(AblyRest):
    """Ably Rest Client"""

    def __init__(self, key: Optional[str] = None, token: Optional[str] = None,
                 token_details: Optional[TokenDetails] = None, **kwargs):
        super().__init__(key, token, token_details, **kwargs)
        self.__http = HttpSync(self, self.options)
        self.__auth = AuthSync(self, self.options)
        self.__http.auth = self.__auth
        self.__channels = ChannelsSync(self)

    def __enter__(self):
        return self

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

    @force_sync
    @catch_all
    async def stats(self, direction: Optional[str] = None, start=None, end=None, params: Optional[dict] = None,
                    limit: Optional[int] = None, paginated=None, unit=None, timeout=None):
        """Returns the stats for this application"""
        return await super().stats(direction, start, end, params, limit, paginated, unit, timeout)

    @force_sync
    @catch_all
    async def time(self, timeout: Optional[float] = None) -> float:
        """Returns the current server time in ms since the unix epoch"""
        return await super().time(timeout)

    @force_sync
    async def request(self, method: str, path: str, version: str, params: Optional[dict] = None,
                      body=None, headers=None):
        return await super().request(method, path, version, params, body, headers)

    def __exit__(self, *excinfo):
        self.close()

    @close_app_eventloop
    async def close(self):
        await super().close()
