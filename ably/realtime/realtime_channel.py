import asyncio
import logging

from ably.realtime.connection import ConnectionState, ProtocolMessageAction
from ably.types.message import Message
from ably.util.exceptions import AblyException
from pyee.asyncio import AsyncIOEventEmitter
from enum import Enum

from ably.util.helper import is_function_or_coroutine

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
        self.__message_emitter = AsyncIOEventEmitter()
        self.__all_messages_emitter = AsyncIOEventEmitter()
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

    async def subscribe(self, *args):
        if isinstance(args[0], str):
            event = args[0]
            if not args[1]:
                raise ValueError("channel.subscribe called without listener")
            if not is_function_or_coroutine(args[1]):
                raise ValueError("subscribe listener must be function or coroutine function")
            listener = args[1]
        elif is_function_or_coroutine(args[0]):
            listener = args[0]
            event = None
        else:
            raise ValueError('invalid subscribe arguments')

        if self.__realtime.connection.state == ConnectionState.CONNECTING:
            await self.__realtime.connection.connect()
        elif self.__realtime.connection.state != ConnectionState.CONNECTED:
            raise AblyException(
                'Cannot subscribe to channel, invalid connection state: {self.__realtime.connection.state}',
                400,
                40000
            )

        if self.state in (ChannelState.INITIALIZED, ChannelState.ATTACHING, ChannelState.DETACHED):
            await self.attach()

        if event is not None:
            self.__message_emitter.on(event, listener)
        else:
            self.__all_messages_emitter.on('message', listener)

        await self.attach()

    def unsubscribe(self, *args):
        if len(args) == 0:
            event = None
            listener = None
        elif isinstance(args[0], str):
            event = args[0]
            if not args[1]:
                raise ValueError("channel.unsubscribe called without listener")
            if not is_function_or_coroutine(args[1]):
                raise ValueError("unsubscribe listener must be a function or coroutine function")
            listener = args[1]
        elif is_function_or_coroutine(args[0]):
            listener = args[0]
            event = None
        else:
            raise ValueError('invalid unsubscribe arguments')

        if listener is None:
            self.__message_emitter.remove_all_listeners()
            self.__all_messages_emitter.remove_all_listeners()
        elif event is not None:
            self.__message_emitter.remove_listener(event, listener)
        else:
            self.__all_messages_emitter.remove_listener('message', listener)

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
        elif action == ProtocolMessageAction.MESSAGE:
            messages = Message.from_encoded_array(msg.get('messages'))
            for message in messages:
                self.__message_emitter.emit(message.name, message)
                self.__all_messages_emitter.emit('message', message)

    def set_state(self, state):
        self.__state = state
        self.emit(state)

    @property
    def name(self):
        return self.__name

    @property
    def state(self):
        return self.__state
