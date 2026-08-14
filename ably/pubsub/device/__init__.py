"""The Ably Pub/Sub client for devices.

Devices are applications running in end-user environments — desktop apps, CLIs,
IoT and embedded clients — whose connections are identified by a `client_id` and
counted on accounts with monthly-active-user billing. This package names that
side, so the client an application should reach for is the one whose package
matches where it runs.

Use `create_client()` to open a realtime connection with channels, presence and
history. It returns the same client `ably` does, with identical behaviour.

Ships in the `ably-pubsub-device` distribution, which adds this subpackage to
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
from ably.util.deprecation import suppress_constructor_deprecation

__version__ = '3.1.2'


def create_client(key: Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None,
                  **kwargs) -> AblyRealtime:
    """Create a device Pub/Sub client: a realtime connection to Ably with
    channels, presence and history.

    Takes the same arguments as `ably.AblyRealtime`, and behaves identically to it.
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
    'create_client',
]
