"""The pubsub packages re-export the core's public surface.

Phase 1 of the package split keeps both sides identical: only the factories
differ. Dropping the parts of the surface that do not belong to a side (push
receive on server, push admin on device) is deferred, so until then a name that
reaches the core and not a side is an omission, and this catches it.
"""

import pytest

import ably
import ably.sync
from ably.pubsub import device, server
from ably.pubsub.server import sync as server_sync

# ably.sync is generated from ably by unasync, so it carries a realtime client
# with the awaits stripped out of code that still calls asyncio. That is an
# artefact of the generation rather than a usable client — nothing tests it, and
# the sync entry point deliberately offers the HTTP client only.
SYNC_ONLY_BY_GENERATION = {'AblyRealtime'}


def exported_types(module):
    """The classes a package offers, which is all the core's __init__ exports."""
    return {name for name in dir(module) if not name.startswith('_') and name[0].isupper()}


@pytest.mark.parametrize('side', [server, device])
def test_side_re_exports_the_core_surface(side):
    assert exported_types(ably) <= set(side.__all__)


def test_the_sync_entry_point_re_exports_the_sync_core_surface():
    assert exported_types(ably.sync) - SYNC_ONLY_BY_GENERATION <= set(server_sync.__all__)


@pytest.mark.parametrize('module', [server, device, server_sync])
def test_everything_declared_public_is_importable(module):
    missing = [name for name in module.__all__ if not hasattr(module, name)]
    assert missing == []
