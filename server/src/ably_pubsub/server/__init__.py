"""The Ably Pub/Sub SDK for servers.

Servers are trusted environments which typically authenticate with an API key,
and whose connections are exempt from monthly-active-user counting. This package
names that side, so the client an application should reach for is the one whose
package matches where it runs.

Use `create_http_client()` for publish, history, presence reads, stats and token
issuing over HTTP, and `create_realtime_client()` when the server also needs to
subscribe to channels or enter presence over a persistent connection. These
factories are the entry points of the `ably-pubsub-server` distribution; the
types they work with are re-exported here so that `ably_pubsub.core`, which is
an internal implementation package, never needs to be imported directly.
"""

import asyncio
from typing import Optional

from ably_pubsub.core import (
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
from ably_pubsub.core.http.paginatedresult import HttpPaginatedResponse, PaginatedResult
from ably_pubsub.core.realtime.channel import RealtimeChannel
from ably_pubsub.core.realtime.connection import Connection
from ably_pubsub.core.realtime.presence import RealtimePresence
from ably_pubsub.core.rest.channel import Channel
from ably_pubsub.core.types.channeldetails import (
    ChannelDetails,
    ChannelMetrics,
    ChannelOccupancy,
    ChannelStatus,
)
from ably_pubsub.core.types.channelstate import ChannelState, ChannelStateChange
from ably_pubsub.core.types.connectionstate import (
    ConnectionEvent,
    ConnectionState,
    ConnectionStateChange,
)
from ably_pubsub.core.types.message import Message, MessageAnnotations
from ably_pubsub.core.types.presence import Presence, PresenceAction, PresenceMessage
from ably_pubsub.core.types.stats import Stats
from ably_pubsub.core.types.tokendetails import TokenDetails
from ably_pubsub.core.types.tokenrequest import TokenRequest

__version__ = '4.0.0'

# The agent identifier declaring the server side.
#
# The `-server` suffix is load-bearing, not cosmetic. On API-key auth the realtime
# system grants the MAU server exemption by matching an agent entry ending in
# `-server`, and an identifier that is not yet in the ably-common registry is
# classified by that suffix alone. Renaming it without preserving the suffix
# silently reclassifies every client this package constructs.
#
# The entry is stamped WITHOUT a version, matching its registration in the
# ably-common agents registry (a pure flag, like `browser`): under lockstep
# versioning a version here always duplicates the ably-pubsub-python entry beside
# it, which keeps carrying identity, version and support status. Wire shape:
#   ably-pubsub-python/4.0.0 python/3.12.1 ably-pubsub-server
SERVER_AGENT_IDENTIFIER = 'ably-pubsub-server'


def _agents_with_side(agents: Optional[dict]) -> dict:
    """Return the caller's agent entries carrying this package's side entry.

    The caller's own entries are preserved, so an SDK layered on top of this
    package keeps its attribution. The side entry is merged last and so wins a
    collision on its own identifier: which side the package declares is the
    package's to state, not the caller's to redefine.
    """
    return {**(agents or {}), SERVER_AGENT_IDENTIFIER: None}


def create_http_client(key: Optional[str] = None, token: Optional[str] = None,
                       token_details: Optional[TokenDetails] = None, **options) -> AblyRest:
    """Create a server Pub/Sub client that operates entirely over HTTP.

    Publishing, history, presence reads, stats and token issuing, with no
    persistent connection. Takes the same arguments as the underlying client
    constructor, and behaves identically to it.
    """
    return AblyRest(key=key, token=token, token_details=token_details,
                    agents=_agents_with_side(options.pop('agents', None)), **options)


def create_realtime_client(key: Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None,
                           **options) -> AblyRealtime:
    """Create a server Pub/Sub client with a persistent realtime connection.

    Everything the HTTP client does, plus subscribing to channels and entering
    presence. Takes the same arguments as the underlying client constructor, and
    behaves identically to it.
    """
    return AblyRealtime(key=key, loop=loop,
                        agents=_agents_with_side(options.pop('agents', None)), **options)


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
    'Channel',
    'ChannelDetails',
    'ChannelMetrics',
    'ChannelMode',
    'ChannelOccupancy',
    'ChannelOptions',
    'ChannelState',
    'ChannelStateChange',
    'ChannelStatus',
    'CipherParams',
    'Connection',
    'ConnectionEvent',
    'ConnectionState',
    'ConnectionStateChange',
    'DeviceDetails',
    'HttpPaginatedResponse',
    'IncompatibleClientIdException',
    'Message',
    'MessageAction',
    'MessageAnnotations',
    'MessageOperation',
    'MessageVersion',
    'Options',
    'PaginatedResult',
    'Presence',
    'PresenceAction',
    'PresenceMessage',
    'PublishResult',
    'Push',
    'PushChannelSubscription',
    'RealtimeChannel',
    'RealtimePresence',
    'SERVER_AGENT_IDENTIFIER',
    'Stats',
    'TokenDetails',
    'TokenRequest',
    'UpdateDeleteResult',
    'VCDiffDecoder',
    'create_http_client',
    'create_realtime_client',
]
