import asyncio
from dataclasses import dataclass
import logging
from typing import Optional

from ably.realtime.connection import ConnectionState, ProtocolMessageAction
from ably.rest.channel import Channel
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
    SUSPENDED = 'suspended'
    FAILED = 'failed'


@dataclass
class ChannelStateChange:
    previous: ChannelState
    current: ChannelState
    reason: Optional[AblyException] = None


class RealtimeChannel(EventEmitter, Channel):
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
        EventEmitter.__init__(self)
        self.__name = name
        self.__attach_future = None
        self.__detach_future = None
        self.__realtime = realtime
        self.__state = ChannelState.INITIALIZED
        self.__message_emitter = EventEmitter()
        self.__timeout_in_secs = self.__realtime.options.realtime_request_timeout / 1000
        Channel.__init__(self, realtime, name, {})

    # RTL4
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
            try:
                await self.__attach_future
            except asyncio.CancelledError:
                raise AblyException("Unable to attach channel due to request timeout", 504, 50003)
            return
        elif self.state == ChannelState.DETACHING:
            try:
                await self.__detach_future
            except asyncio.CancelledError:
                raise AblyException("Unable to detach channel due to request timeout", 504, 50003)
            return

        self._request_state(ChannelState.ATTACHING)

        # RTL4i - wait for pending connection
        if self.__realtime.connection.state == ConnectionState.CONNECTING:
            await self.__realtime.connect()

        self.__attach_future = asyncio.Future()

        self._attach_impl()

        try:
            await asyncio.wait_for(self.__attach_future, self.__timeout_in_secs)  # RTL4f
        except asyncio.TimeoutError:
            raise AblyException("Timeout waiting for channel attach", 504, 50003)
        self._request_state(ChannelState.ATTACHED)

    def _attach_impl(self):
        log.info("RealtimeChannel.attach_impl(): sending ATTACH protocol message")

        # RTL4c
        attach_msg = {
            "action": ProtocolMessageAction.ATTACH,
            "channel": self.name,
        }
        self._send_message(attach_msg)

    # RTL5
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

        # RTL5g, RTL5b - raise exception if state invalid
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
            try:
                await self.__detach_future
            except asyncio.CancelledError:
                raise AblyException("Unable to detach channel due to request timeout", 504, 50003)
            return
        elif self.state == ChannelState.ATTACHING:
            try:
                await self.__attach_future
            except asyncio.CancelledError:
                raise AblyException("Unable to attach channel due to request timeout", 504, 50003)

        self._notify_state(ChannelState.DETACHING)

        # RTL5h - wait for pending connection
        if self.__realtime.connection.state == ConnectionState.CONNECTING:
            await self.__realtime.connect()

        self.__detach_future = asyncio.Future()

        # RTL5d
        detach_msg = {
            "action": ProtocolMessageAction.DETACH,
            "channel": self.name,
        }
        self._send_message(detach_msg)

        try:
            await asyncio.wait_for(self.__detach_future, self.__timeout_in_secs)  # RTL5f
        except asyncio.TimeoutError:
            raise AblyException("Timeout waiting for channel detach", 504, 50003)
        self._notify_state(ChannelState.DETACHED)

    # RTL7
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

        # RTL7c
        if self.state in (ChannelState.INITIALIZED, ChannelState.ATTACHING, ChannelState.DETACHED):
            await self.attach()

        if event is not None:
            # RTL7b
            self.__message_emitter.on(event, listener)
        else:
            # RTL7a
            self.__message_emitter.on(listener)

        await self.attach()

    # RTL8
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
            # RTL8c
            self.__message_emitter.off()
        elif event is not None:
            # RTL8b
            self.__message_emitter.off(event, listener)
        else:
            # RTL8a
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

    def _request_state(self, state: ChannelState):
        log.info(f'RealtimeChannel._request_state(): state = {state}')
        self._notify_state(state)

    def _notify_state(self, state: ChannelState, reason=None):
        log.info(f'RealtimeChannel._notify_state(): state = {state}')

        if state == self.state:
            return

        state_change = ChannelStateChange(self.__state, state, reason=reason)

        self.__state = state
        self._emit(state, state_change)

    def _send_message(self, msg):
        asyncio.create_task(self.__realtime.connection.connection_manager.send_protocol_message(msg))

    # RTL23
    @property
    def name(self):
        """Returns channel name"""
        return self.__name

    # RTL2b
    @property
    def state(self):
        """Returns channel state"""
        return self.__state
