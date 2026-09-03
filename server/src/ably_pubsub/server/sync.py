"""The synchronous flavour of the Ably Pub/Sub SDK for servers.

Offers the HTTP client without an event loop. There is no synchronous realtime
client, so a server that needs to subscribe should use
`ably_pubsub.server.create_realtime_client()` instead.

Hand-written rather than generated: the code generator that produces
`ably_pubsub.core.sync` runs over the core distribution only.
"""

from typing import Optional

from ably_pubsub.core.sync import (
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
from ably_pubsub.core.sync.types.tokendetails import TokenDetails
from ably_pubsub.server import SERVER_AGENT_IDENTIFIER, _agents_with_side


def create_http_client(key: Optional[str] = None, token: Optional[str] = None,
                       token_details: Optional[TokenDetails] = None, **options) -> AblyRestSync:
    """Create a synchronous server Pub/Sub client that operates entirely over HTTP.

    Takes the same arguments as the underlying client constructor, and behaves
    identically to it.
    """
    return AblyRestSync(key=key, token=token, token_details=token_details,
                        agents=_agents_with_side(options.pop('agents', None)), **options)


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
    'SERVER_AGENT_IDENTIFIER',
    'TokenDetails',
    'UpdateDeleteResult',
    'VCDiffDecoder',
    'create_http_client',
]
