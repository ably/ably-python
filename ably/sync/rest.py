import logging
from typing import Optional
from ably.util.exceptions import catch_all
from ably.rest.rest import AblyRest

log = logging.getLogger(__name__)


class AblyRestSync(AblyRest):
    """Ably Rest Client"""
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
