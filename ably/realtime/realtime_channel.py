import asyncio
import logging

from ably.realtime.connection import ConnectionState, ProtocolMessageAction
from ably.types.message import Message
from ably.util.eventemitter import EventEmitter
from ably.util.exceptions import AblyException
from enum import Enum

from ably.util.helper import is_callable_or_coroutine

log = logging.getLogger(__name__)


class ChannelState(str, Enum):
    INITIALIZED = 'initialized'
    ATTACHING = 'attaching'
    ATTACHED = 'attached'
    DETACHING = 'detaching'
    DETACHED = 'detached'


class RealtimeChannel(EventEmitter):
    """
    Ably Realtime Channel

    Attributes
    ----------
    name: str
        Channel name
    state: str
        Channel state

    Methods
    -------
    attach()
        Attach to channel
    detach()
        Detach from channel
    subscribe(*args)
        Subscribe to messages on a channel
    unsubscribe(*args)
        Unsubscribe to messages from a channel
    """

    def __init__(self, realtime, name):
        self.__name = name
        self.__attach_future = None
        self.__detach_future = None
        self.__realtime = realtime
        self.__state = ChannelState.INITIALIZED
        self.__message_emitter = EventEmitter()
        super().__init__()

    async def attach(self):
        """Attach to channel

        Attach to this channel ensuring the channel is created in the Ably system and all messages published
        on the channel are received by any channel listeners registered using subscribe

        Raises
        ------
        AblyException
            If unable to attach channel
        """

        log.info(f'RealtimeChannel.attach() called, channel = {self.name}')

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
        await self.__realtime.connection.connection_manager.send_protocol_message(
            {
                "action": ProtocolMessageAction.ATTACH,
                "channel": self.name,
            }
        )
        await self.__attach_future
        self.set_state(ChannelState.ATTACHED)

    async def detach(self):
        """Detach from channel

        Any resulting channel state change is emitted to any listeners registered
        Once all clients globally have detached from the channel, the channel will be released
        in the Ably service within two minutes.

        Raises
        ------
        AblyException
            If unable to detach channel
        """

        log.info(f'RealtimeChannel.detach() called, channel = {self.name}')

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
        await self.__realtime.connection.connection_manager.send_protocol_message(
            {
                "action": ProtocolMessageAction.DETACH,
                "channel": self.name,
            }
        )
        await self.__detach_future
        self.set_state(ChannelState.DETACHED)

    async def subscribe(self, *args):
        """Subscribe to a channel

        Registers a listener for messages on the channel.
        The caller supplies a listener function, which is called
        each time one or more messages arrives on the channel.

        The function resolves once the channel is attached.

        Parameters
        ----------
        *args: event, listener
            Subscribe event and listener

            arg1(event): str, optional
                Subscribe to messages with the given event name

            arg2(listener): callable
                Subscribe to all messages on the channel

            When no event is provided, arg1 is used as the listener.

        Raises
        ------
        AblyException
            If unable to subscribe to a channel due to invalid connection state
        ValueError
            If no valid subscribe arguments are passed
        """
        if isinstance(args[0], str):
            event = args[0]
            if not args[1]:
                raise ValueError("channel.subscribe called without listener")
            if not is_callable_or_coroutine(args[1]):
                raise ValueError("subscribe listener must be function or coroutine function")
            listener = args[1]
        elif is_callable_or_coroutine(args[0]):
            listener = args[0]
            event = None
        else:
            raise ValueError('invalid subscribe arguments')

        log.info(f'RealtimeChannel.subscribe called, channel = {self.name}, event = {event}')

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
            self.__message_emitter.on(listener)

        await self.attach()

    def unsubscribe(self, *args):
        """Unsubscribe from a channel

        Deregister the given listener for (for any/all event names).
        This removes an earlier event-specific subscription.

        Parameters
        ----------
        *args: event, listener
            Unsubscribe event and listener

            arg1(event): str, optional
                Unsubscribe to messages with the given event name

            arg2(listener): callable
                Unsubscribe to all messages on the channel

            When no event is provided, arg1 is used as the listener.

        Raises
        ------
        ValueError
            If no valid unsubscribe arguments are passed, no listener or listener is not a function
            or coroutine
        """
        if len(args) == 0:
            event = None
            listener = None
        elif isinstance(args[0], str):
            event = args[0]
            if not args[1]:
                raise ValueError("channel.unsubscribe called without listener")
            if not is_callable_or_coroutine(args[1]):
                raise ValueError("unsubscribe listener must be a function or coroutine function")
            listener = args[1]
        elif is_callable_or_coroutine(args[0]):
            listener = args[0]
            event = None
        else:
            raise ValueError('invalid unsubscribe arguments')

        log.info(f'RealtimeChannel.unsubscribe called, channel = {self.name}, event = {event}')

        if listener is None:
            self.__message_emitter.off()
        elif event is not None:
            self.__message_emitter.off(event, listener)
        else:
            self.__message_emitter.off(listener)

    def _on_message(self, msg):
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
                self.__message_emitter._emit(message.name, message)

    def set_state(self, state):
        self.__state = state
        self._emit(state)

    @property
    def name(self):
        """Returns channel name"""
        return self.__name

    @property
    def state(self):
        """Returns channel state"""
        return self.__state
