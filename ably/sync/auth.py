from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING, Union

from ably import Auth
from ably.types.options import Options

if TYPE_CHECKING:
    from ably.rest.rest import AblyRest
    from ably.realtime.realtime import AblyRealtime

__all__ = ["AuthSync"]

log = logging.getLogger(__name__)


class AuthSync(Auth):

    async def get_auth_transport_param(self):
        return super().get_auth_transport_param()

    async def authorize(self, token_params: Optional[dict] = None, auth_options=None):
        return super().authorize(token_params, auth_options)

    async def request_token(self, token_params: Optional[dict] = None,
                            # auth_options
                            key_name: Optional[str] = None, key_secret: Optional[str] = None, auth_callback=None,
                            auth_url: Optional[str] = None, auth_method: Optional[str] = None,
                            auth_headers: Optional[dict] = None, auth_params: Optional[dict] = None,
                            query_time=None):
        return super().request_token(token_params, key_name, key_secret, auth_callback, auth_url, auth_method,
                                     auth_headers, auth_params, query_time)

    async def create_token_request(self, token_params: Optional[dict] = None, key_name: Optional[str] = None,
                                   key_secret: Optional[str] = None, query_time=None):
        return super().create_token_request(token_params, key_name, key_secret, query_time
                                            )

    async def token_request_from_auth_url(self, method: str, url: str, token_params,
                                          headers, auth_params):
        return super().token_request_from_auth_url(method, url, token_params, headers, auth_params)
