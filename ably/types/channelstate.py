from dataclasses import dataclass
from typing import Optional
from enum import Enum
from ably.util.exceptions import AblyException


class ChannelState(str, Enum):
    INITIALIZED = 'initialized'
    ATTACHING = 'attaching'
    ATTACHED = 'attached'
    DETACHING = 'detaching'
    DETACHED = 'detached'
    SUSPENDED = 'suspended'
    FAILED = 'failed'


@dataclass
class ChannelStateChange:
    previous: ChannelState
    current: ChannelState
    resumed: bool
    reason: Optional[AblyException] = None
