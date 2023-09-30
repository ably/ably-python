from __future__ import annotations
import logging
from typing import Optional

from ably import Auth
__all__ = ["AuthSync"]

from ably.decorator.sync import force_sync

log = logging.getLogger(__name__)


class AuthSync(Auth):

    @force_sync
    async def get_auth_transport_param(self):
        return await super().get_auth_transport_param()

    @force_sync
    async def authorize(self, token_params: Optional[dict] = None, auth_options=None):
        return super().authorize(token_params, auth_options)

    @force_sync
    async def request_token(self, token_params: Optional[dict] = None,
                            # auth_options
                            key_name: Optional[str] = None, key_secret: Optional[str] = None, auth_callback=None,
                            auth_url: Optional[str] = None, auth_method: Optional[str] = None,
                            auth_headers: Optional[dict] = None, auth_params: Optional[dict] = None,
                            query_time=None):
        return super().request_token(token_params, key_name, key_secret, auth_callback, auth_url, auth_method,
                                     auth_headers, auth_params, query_time)

    @force_sync
    async def create_token_request(self, token_params: Optional[dict] = None, key_name: Optional[str] = None,
                                   key_secret: Optional[str] = None, query_time=None):
        return super().create_token_request(token_params, key_name, key_secret, query_time
                                            )

    @force_sync
    async def token_request_from_auth_url(self, method: str, url: str, token_params,
                                          headers, auth_params):
        return super().token_request_from_auth_url(method, url, token_params, headers, auth_params)
