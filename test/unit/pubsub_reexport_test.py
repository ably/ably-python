"""The server package re-exports the core's public surface.

`ably_pubsub.core` is an internal implementation package: consumers are meant to
reach only for `ably_pubsub.server`. So every type the core declares public has
to reach the server package too, or it is unreachable by supported means.
Trimming the surface to what a server actually needs is a later change (091d);
until then, a name that reaches the core and not the server is an omission, and
this catches it.
"""

import ably_pubsub.core
import ably_pubsub.core.sync
import ably_pubsub.server
from ably_pubsub.server import sync as server_sync

# ably_pubsub.core.sync is generated from ably_pubsub.core by unasync, so it
# carries a realtime client with the awaits stripped out of code that still
# calls asyncio. That is an artefact of the generation rather than a usable
# client — nothing tests it, and the sync entry point deliberately offers the
# HTTP client only.
SYNC_ONLY_BY_GENERATION = {'AblyRealtime'}


def exported_types(module):
    """The classes a package offers, which is all the core's __init__ exports."""
    return {name for name in dir(module) if not name.startswith('_') and name[0].isupper()}


def test_the_server_re_exports_the_core_surface():
    assert exported_types(ably_pubsub.core) <= set(ably_pubsub.server.__all__)


def test_the_sync_door_re_exports_the_sync_core_surface():
    assert exported_types(ably_pubsub.core.sync) - SYNC_ONLY_BY_GENERATION <= set(server_sync.__all__)


# 3.x users reached for these under `ably.types.*` and `ably.http.*`, which have no
# supported 4.0 equivalent outside the internal core — so they have to be nameable
# from the server package or they are not nameable at all. Guarding the list keeps
# a future trim of the surface (091d) from dropping one silently.
REACHABLE_BY_A_CONSUMER = {
    'Channel',
    'ChannelDetails',
    'ChannelMetrics',
    'ChannelOccupancy',
    'ChannelState',
    'ChannelStateChange',
    'ChannelStatus',
    'Connection',
    'ConnectionEvent',
    'ConnectionState',
    'ConnectionStateChange',
    'HttpPaginatedResponse',
    'Message',
    'MessageAnnotations',
    'PaginatedResult',
    'Presence',
    'PresenceAction',
    'PresenceMessage',
    'RealtimeChannel',
    'RealtimePresence',
    'Stats',
    'TokenDetails',
    'TokenRequest',
}

# The sync flavour has no realtime client, so the realtime object and state types
# have no counterpart there; unasync renames the rest.
SYNC_REACHABLE_BY_A_CONSUMER = (REACHABLE_BY_A_CONSUMER - {
    'Channel',
    'ChannelState',
    'ChannelStateChange',
    'Connection',
    'ConnectionEvent',
    'ConnectionState',
    'ConnectionStateChange',
    'HttpPaginatedResponse',
    'PaginatedResult',
    'RealtimeChannel',
    'RealtimePresence',
}) | {'ChannelSync', 'HttpPaginatedResponseSync', 'PaginatedResultSync'}


def test_the_types_a_consumer_names_are_reachable_from_the_server_package():
    assert REACHABLE_BY_A_CONSUMER <= set(ably_pubsub.server.__all__)
    missing = [name for name in REACHABLE_BY_A_CONSUMER if not hasattr(ably_pubsub.server, name)]
    assert missing == []


def test_the_types_a_consumer_names_are_reachable_from_the_sync_door():
    assert SYNC_REACHABLE_BY_A_CONSUMER <= set(server_sync.__all__)
    missing = [name for name in SYNC_REACHABLE_BY_A_CONSUMER if not hasattr(server_sync, name)]
    assert missing == []
