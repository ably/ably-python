import asyncio
import logging
from ably.realtime.connection import ConnectionState, ProtocolMessageAction
from ably.util.exceptions import AblyException
from pyee.asyncio import AsyncIOEventEmitter
from enum import Enum

log = logging.getLogger(__name__)


class ChannelState(Enum):
    INITIALIZED = 'initialized'
    ATTACHING = 'attaching'
    ATTACHED = 'attached'
    DETACHING = 'detaching'
    DETACHED = 'detached'


class RealtimeChannel(AsyncIOEventEmitter):
    def __init__(self, realtime, name):
        self.__name = name
        self.__attach_future = None
        self.__detach_future = None
        self.__realtime = realtime
        self.__state = ChannelState.INITIALIZED
        super().__init__()

    async def attach(self):
        # RTL4a - if channel is attached do nothing
        if self.state == ChannelState.ATTACHED:
            return

        # RTL4b
        if self.__realtime.connection.state not in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            raise AblyException(
                message=f"Unable to attach; channel state = {self.state}",
                code=90001,
                status_code=400
            )

        # RTL4h - wait for pending attach/detach
        if self.state == ChannelState.ATTACHING:
            await self.__attach_future
            return
        elif self.state == ChannelState.DETACHING:
            await self.__detach_future

        self.set_state(ChannelState.ATTACHING)

        # RTL4i - wait for pending connection
        if self.__realtime.connection.state == ConnectionState.CONNECTING:
            await self.__realtime.connect()

        self.__attach_future = asyncio.Future()
        await self.__realtime.connection.connection_manager.sendProtocolMessage(
            {
                "action": ProtocolMessageAction.ATTACH,
                "channel": self.name,
            }
        )
        await self.__attach_future
        self.set_state(ChannelState.ATTACHED)

    async def detach(self):
        # RTL5g - raise exception if state invalid
        if self.__realtime.connection.state in [ConnectionState.CLOSING, ConnectionState.FAILED]:
            raise AblyException(
                message=f"Unable to detach; channel state = {self.state}",
                code=90001,
                status_code=400
            )

        # RTL5a - if channel already detached do nothing
        if self.state in [ChannelState.INITIALIZED, ChannelState.DETACHED]:
            return

        # RTL5i - wait for pending attach/detach
        if self.state == ChannelState.DETACHING:
            await self.__detach_future
            return
        elif self.state == ChannelState.ATTACHING:
            await self.__attach_future

        self.set_state(ChannelState.DETACHING)

        # RTL5h - wait for pending connection
        if self.__realtime.connection.state == ConnectionState.CONNECTING:
            await self.__realtime.connect()

        self.__detach_future = asyncio.Future()
        await self.__realtime.connection.connection_manager.sendProtocolMessage(
            {
                "action": ProtocolMessageAction.DETACH,
                "channel": self.name,
            }
        )
        await self.__detach_future
        self.set_state(ChannelState.DETACHED)

    def on_message(self, msg):
        action = msg.get('action')
        if action == ProtocolMessageAction.ATTACHED:
            if self.__attach_future:
                self.__attach_future.set_result(None)
            self.__attach_future = None
        elif action == ProtocolMessageAction.DETACHED:
            if self.__detach_future:
                self.__detach_future.set_result(None)
            self.__detach_future = None

    def set_state(self, state):
        self.__state = state
        self.emit(state)

    @property
    def name(self):
        return self.__name

    @property
    def state(self):
        return self.__state
