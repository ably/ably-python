"""The synchronous flavour of the Ably Pub/Sub client for servers.

Mirrors `ably.sync`, which offers the HTTP client without an event loop. There
is no synchronous realtime client, so a server that needs to subscribe should
use `ably.pubsub.server.create_realtime_client()` instead.
"""

from typing import Optional

from ably.sync import (
    AblyAuthException,
    AblyException,
    AblyRestSync,
    AblyVCDiffDecoder,
    Annotation,
    AnnotationAction,
    AuthSync,
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
    PushChannelSubscription,
    PushSync,
    UpdateDeleteResult,
    VCDiffDecoder,
)
from ably.sync.types.tokendetails import TokenDetails
from ably.sync.util.deprecation import suppress_constructor_deprecation


def create_http_client(key: Optional[str] = None, token: Optional[str] = None,
                       token_details: Optional[TokenDetails] = None, **kwargs) -> AblyRestSync:
    """Create a synchronous server Pub/Sub client that operates entirely over HTTP.

    Takes the same arguments as `ably.sync.AblyRestSync`, and behaves identically
    to it.
    """
    with suppress_constructor_deprecation():
        return AblyRestSync(key=key, token=token, token_details=token_details, **kwargs)


__all__ = [
    'AblyAuthException',
    'AblyException',
    'AblyRestSync',
    'AblyVCDiffDecoder',
    'Annotation',
    'AnnotationAction',
    'AuthSync',
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
    'PushChannelSubscription',
    'PushSync',
    'UpdateDeleteResult',
    'VCDiffDecoder',
    'create_http_client',
]
