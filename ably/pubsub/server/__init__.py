"""The Ably Pub/Sub client for servers.

Servers are trusted environments which typically authenticate with an API key,
and whose connections are exempt from monthly-active-user counting. This package
names that side, so the client an application should reach for is the one whose
package matches where it runs.

Use `create_http_client()` for publish, history, presence reads, stats and token
issuing over HTTP, and `create_realtime_client()` when the server also needs to
subscribe to channels or enter presence over a persistent connection. Both
return the same clients `ably` does, with identical behaviour.

Ships in the `ably-pubsub-server` distribution, which adds this subpackage to
the `ably` package installed by the `ably` distribution.
"""

import asyncio
from typing import Optional

from ably import (
    AblyAuthException,
    AblyException,
    AblyRealtime,
    AblyRest,
    AblyVCDiffDecoder,
    Annotation,
    AnnotationAction,
    Auth,
    Capability,
    ChannelMode,
    ChannelOptions,
    CipherParams,
    DeviceDetails,
    IncompatibleClientIdException,
    MessageAction,
    MessageOperation,
    MessageVersion,
    Options,
    PublishResult,
    Push,
    PushChannelSubscription,
    UpdateDeleteResult,
    VCDiffDecoder,
)
from ably.types.tokendetails import TokenDetails
from ably.util.deprecation import suppress_constructor_deprecation

__version__ = '3.1.2'


def create_http_client(key: Optional[str] = None, token: Optional[str] = None,
                       token_details: Optional[TokenDetails] = None, **kwargs) -> AblyRest:
    """Create a server Pub/Sub client that operates entirely over HTTP.

    Takes the same arguments as `ably.AblyRest`, and behaves identically to it.
    """
    with suppress_constructor_deprecation():
        return AblyRest(key=key, token=token, token_details=token_details, **kwargs)


def create_realtime_client(key: Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None,
                           **kwargs) -> AblyRealtime:
    """Create a server Pub/Sub client with a persistent realtime connection.

    Everything the HTTP client does, plus subscribing to channels and entering
    presence. Takes the same arguments as `ably.AblyRealtime`, and behaves
    identically to it.
    """
    with suppress_constructor_deprecation():
        return AblyRealtime(key=key, loop=loop, **kwargs)


__all__ = [
    'AblyAuthException',
    'AblyException',
    'AblyRealtime',
    'AblyRest',
    'AblyVCDiffDecoder',
    'Annotation',
    'AnnotationAction',
    'Auth',
    'Capability',
    'ChannelMode',
    'ChannelOptions',
    'CipherParams',
    'DeviceDetails',
    'IncompatibleClientIdException',
    'MessageAction',
    'MessageOperation',
    'MessageVersion',
    'Options',
    'PublishResult',
    'Push',
    'PushChannelSubscription',
    'UpdateDeleteResult',
    'VCDiffDecoder',
    'create_http_client',
    'create_realtime_client',
]
