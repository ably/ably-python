from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING, Dict, Any
from ably.realtime.connection import ConnectionState
from ably.rest.channel import Channel, Channels as RestChannels
from ably.transport.websockettransport import ProtocolMessageAction
from ably.types.channelstate import ChannelState, ChannelStateChange
from ably.types.flags import Flag, has_flag
from ably.types.message import Message
from ably.types.mixins import DecodingContext
from ably.util.eventemitter import EventEmitter
from ably.util.exceptions import AblyException
from ably.util.helper import Timer, is_callable_or_coroutine

if TYPE_CHECKING:
    from ably.realtime.realtime import AblyRealtime
    from ably.util.crypto import CipherParams

log = logging.getLogger(__name__)


class ChannelOptions:
    """Channel options for Ably Realtime channels

    Attributes
    ----------
    cipher : CipherParams, optional
        Requests encryption for this channel when not null, and specifies encryption-related parameters.
    params : Dict[str, str], optional
        Channel parameters that configure the behavior of the channel.
    """

    def __init__(self, cipher: Optional[CipherParams] = None, params: Optional[dict] = None):
        self.__cipher = cipher
        self.__params = params
        # Validate params
        if self.__params and not isinstance(self.__params, dict):
            raise AblyException("params must be a dictionary", 40000, 400)

    @property
    def cipher(self):
        """Get cipher configuration"""
        return self.__cipher

    @property
    def params(self) -> Dict[str, str]:
        """Get channel parameters"""
        return self.__params

    def __eq__(self, other):
        """Check equality with another ChannelOptions instance"""
        if not isinstance(other, ChannelOptions):
            return False

        return (self.__cipher == other.__cipher and
                self.__params == other.__params)

    def __hash__(self):
        """Make ChannelOptions hashable"""
        return hash((
            self.__cipher,
            tuple(sorted(self.__params.items())) if self.__params else None,
        ))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = {}
        if self.__cipher is not None:
            result['cipher'] = self.__cipher
        if self.__params:
            result['params'] = self.__params
        return result

    @classmethod
    def from_dict(cls, options_dict: Dict[str, Any]) -> 'ChannelOptions':
        """Create ChannelOptions from dictionary"""
        if not isinstance(options_dict, dict):
            raise AblyException("options must be a dictionary", 40000, 400)

        return cls(
            cipher=options_dict.get('cipher'),
            params=options_dict.get('params'),
        )


class RealtimeChannel(EventEmitter, Channel):
    """
    Ably Realtime Channel

    Attributes
    ----------
    name: str
        Channel name
    state: str
        Channel state
    error_reason: AblyException
        An AblyException instance describing the last error which occurred on the channel, if any.

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

    def __init__(self, realtime: AblyRealtime, name: str, channel_options: Optional[ChannelOptions] = None):
        EventEmitter.__init__(self)
        self.__name = name
        self.__realtime = realtime
        self.__state = ChannelState.INITIALIZED
        self.__message_emitter = EventEmitter()
        self.__state_timer: Optional[Timer] = None
        self.__attach_resume = False
        self.__attach_serial: Optional[str] = None
        self.__channel_serial: Optional[str] = None
        self.__retry_timer: Optional[Timer] = None
        self.__error_reason: Optional[AblyException] = None
        self.__channel_options = channel_options or ChannelOptions()
        self.__params: Optional[Dict[str, str]] = None

        # Delta-specific fields for RTL19/RTL20 compliance
        vcdiff_decoder = self.__realtime.options.vcdiff_decoder if self.__realtime.options.vcdiff_decoder else None
        self.__decoding_context = DecodingContext(vcdiff_decoder=vcdiff_decoder)
        self.__decode_failure_recovery_in_progress = False

        # Used to listen to state changes internally, if we use the public event emitter interface then internals
        # will be disrupted if the user called .off() to remove all listeners
        self.__internal_state_emitter = EventEmitter()

        # Pass channel options as dictionary to parent Channel class
        Channel.__init__(self, realtime, name, self.__channel_options.to_dict())

    async def set_options(self, channel_options: ChannelOptions) -> None:
        """Set channel options"""
        should_reattach = self.should_reattach_to_set_options(channel_options)
        self.set_options_without_reattach(channel_options)

        if should_reattach:
            self._attach_impl()
            state_change = await self.__internal_state_emitter.once_async()
            if state_change.current in (ChannelState.SUSPENDED, ChannelState.FAILED):
                raise state_change.reason

    def set_options_without_reattach(self, channel_options: ChannelOptions) -> None:
        """Internal method"""
        self.__channel_options = channel_options
        # Update parent class options
        self.options = channel_options.to_dict()

    # RTL4
    async def attach(self) -> None:
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

        self.__error_reason = None

        # RTL4b
        if self.__realtime.connection.state not in [
            ConnectionState.CONNECTING,
            ConnectionState.CONNECTED,
            ConnectionState.DISCONNECTED
        ]:
            raise AblyException(
                message=f"Unable to attach; channel state = {self.state}",
                code=90001,
                status_code=400
            )

        if self.state != ChannelState.ATTACHING:
            self._request_state(ChannelState.ATTACHING)

        state_change = await self.__internal_state_emitter.once_async()

        if state_change.current in (ChannelState.SUSPENDED, ChannelState.FAILED):
            raise state_change.reason

    def _attach_impl(self):
        log.debug("RealtimeChannel.attach_impl(): sending ATTACH protocol message")

        # RTL4c
        attach_msg = {
            "action": ProtocolMessageAction.ATTACH,
            "params": self.__channel_options.params,
            "channel": self.name,
        }

        if self.__attach_resume:
            attach_msg["flags"] = Flag.ATTACH_RESUME
        if self.__channel_serial:
            attach_msg["channelSerial"] = self.__channel_serial

        self._send_message(attach_msg)

    # RTL5
    async def detach(self) -> None:
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

        if self.state == ChannelState.SUSPENDED:
            self._notify_state(ChannelState.DETACHED)
            return
        elif self.state == ChannelState.FAILED:
            raise AblyException("Unable to detach; channel state = failed", 90001, 400)
        else:
            self._request_state(ChannelState.DETACHING)

        # RTL5h - wait for pending connection
        if self.__realtime.connection.state == ConnectionState.CONNECTING:
            self.__realtime.connect()

        state_change = await self.__internal_state_emitter.once_async()
        new_state = state_change.current

        if new_state == ChannelState.DETACHED:
            return
        elif new_state == ChannelState.ATTACHING:
            raise AblyException("Detach request superseded by a subsequent attach request", 90000, 409)
        else:
            raise state_change.reason

    def _detach_impl(self) -> None:
        log.debug("RealtimeChannel.detach_impl(): sending DETACH protocol message")

        # RTL5d
        detach_msg = {
            "action": ProtocolMessageAction.DETACH,
            "channel": self.__name,
        }

        self._send_message(detach_msg)

    # RTL7
    async def subscribe(self, *args) -> None:
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

        if event is not None:
            # RTL7b
            self.__message_emitter.on(event, listener)
        else:
            # RTL7a
            self.__message_emitter.on(listener)

        # RTL7c
        await self.attach()

    # RTL8
    def unsubscribe(self, *args) -> None:
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

    def _on_message(self, proto_msg: dict) -> None:
        action = proto_msg.get('action')
        # RTL4c1
        channel_serial = proto_msg.get('channelSerial')
        # TM2a, TM2c, TM2f
        Message.update_inner_message_fields(proto_msg)

        if action == ProtocolMessageAction.ATTACHED:
            flags = proto_msg.get('flags')
            error = proto_msg.get("error")
            exception = None
            resumed = False

            self.__attach_serial = channel_serial
            self.__channel_serial = channel_serial
            self.__params = proto_msg.get('params')

            if error:
                exception = AblyException.from_dict(error)

            if flags:
                resumed = has_flag(flags, Flag.RESUMED)

            #  RTL12
            if self.state == ChannelState.ATTACHED:
                if not resumed:
                    state_change = ChannelStateChange(self.state, ChannelState.ATTACHED, resumed, exception)
                    self._emit("update", state_change)
            elif self.state == ChannelState.ATTACHING:
                self._notify_state(ChannelState.ATTACHED, resumed=resumed)
            else:
                log.warn("RealtimeChannel._on_message(): ATTACHED received while not attaching")
        elif action == ProtocolMessageAction.DETACHED:
            if self.state == ChannelState.DETACHING:
                self._notify_state(ChannelState.DETACHED)
            elif self.state == ChannelState.ATTACHING:
                self._notify_state(ChannelState.SUSPENDED)
            else:
                self._request_state(ChannelState.ATTACHING)
        elif action == ProtocolMessageAction.MESSAGE:
            messages = []
            try:
                messages = Message.from_encoded_array(proto_msg.get('messages'), context=self.__decoding_context)
                self.__decoding_context.last_message_id = messages[-1].id
                self.__channel_serial = channel_serial
            except AblyException as e:
                if e.code == 40018:  # Delta decode failure - start recovery
                    self._start_decode_failure_recovery(e)
                else:
                    log.error(f"Message processing error {e}. Skip messages {proto_msg.get('messages')}")
            for message in messages:
                self.__message_emitter._emit(message.name, message)
        elif action == ProtocolMessageAction.ERROR:
            error = AblyException.from_dict(proto_msg.get('error'))
            self._notify_state(ChannelState.FAILED, reason=error)

    def _request_state(self, state: ChannelState) -> None:
        log.debug(f'RealtimeChannel._request_state(): state = {state}')
        self._notify_state(state)
        self._check_pending_state()

    def _notify_state(self, state: ChannelState, reason: Optional[AblyException] = None,
                      resumed: bool = False) -> None:
        log.debug(f'RealtimeChannel._notify_state(): state = {state}')

        self.__clear_state_timer()

        if state == self.state:
            return

        if reason is not None:
            self.__error_reason = reason

        if state == ChannelState.INITIALIZED:
            self.__error_reason = None

        if state == ChannelState.SUSPENDED and self.ably.connection.state == ConnectionState.CONNECTED:
            self.__start_retry_timer()
        else:
            self.__cancel_retry_timer()

        # RTL4j1
        if state == ChannelState.ATTACHED:
            self.__attach_resume = True
        if state in (ChannelState.DETACHING, ChannelState.FAILED):
            self.__attach_resume = False

        # RTP5a1
        if state in (ChannelState.DETACHED, ChannelState.SUSPENDED, ChannelState.FAILED):
            self.__channel_serial = None

        if state != ChannelState.ATTACHING:
            self.__decode_failure_recovery_in_progress = False

        state_change = ChannelStateChange(self.__state, state, resumed, reason=reason)

        self.__state = state
        self._emit(state, state_change)
        self.__internal_state_emitter._emit(state, state_change)

    def _send_message(self, msg: dict) -> None:
        asyncio.create_task(self.__realtime.connection.connection_manager.send_protocol_message(msg))

    def _check_pending_state(self):
        connection_state = self.__realtime.connection.connection_manager.state

        if connection_state is not ConnectionState.CONNECTED:
            log.debug(f"RealtimeChannel._check_pending_state(): connection state = {connection_state}")
            return

        if self.state == ChannelState.ATTACHING:
            self.__start_state_timer()
            self._attach_impl()
        elif self.state == ChannelState.DETACHING:
            self.__start_state_timer()
            self._detach_impl()

    def __start_state_timer(self) -> None:
        if not self.__state_timer:
            def on_timeout() -> None:
                log.debug('RealtimeChannel.start_state_timer(): timer expired')
                self.__state_timer = None
                self.__timeout_pending_state()

            self.__state_timer = Timer(self.__realtime.options.realtime_request_timeout, on_timeout)

    def __clear_state_timer(self) -> None:
        if self.__state_timer:
            self.__state_timer.cancel()
            self.__state_timer = None

    def __timeout_pending_state(self) -> None:
        if self.state == ChannelState.ATTACHING:
            self._notify_state(
                ChannelState.SUSPENDED, reason=AblyException("Channel attach timed out", 408, 90007))
        elif self.state == ChannelState.DETACHING:
            self._notify_state(ChannelState.ATTACHED, reason=AblyException("Channel detach timed out", 408, 90007))
        else:
            self._check_pending_state()

    def __start_retry_timer(self) -> None:
        if self.__retry_timer:
            return

        self.__retry_timer = Timer(self.ably.options.channel_retry_timeout, self.__on_retry_timer_expire)

    def __cancel_retry_timer(self) -> None:
        if self.__retry_timer:
            self.__retry_timer.cancel()
            self.__retry_timer = None

    def __on_retry_timer_expire(self) -> None:
        if self.state == ChannelState.SUSPENDED and self.ably.connection.state == ConnectionState.CONNECTED:
            self.__retry_timer = None
            log.info("RealtimeChannel retry timer expired, attempting a new attach")
            self._request_state(ChannelState.ATTACHING)

    def should_reattach_to_set_options(self, new_options: ChannelOptions) -> bool:
        """Internal method"""
        if self.state != ChannelState.ATTACHING and self.state != ChannelState.ATTACHED:
            return False
        return self.__channel_options != new_options

    # RTL23
    @property
    def name(self) -> str:
        """Returns channel name"""
        return self.__name

    # RTL2b
    @property
    def state(self) -> ChannelState:
        """Returns channel state"""
        return self.__state

    @state.setter
    def state(self, state: ChannelState) -> None:
        self.__state = state

    # RTL24
    @property
    def error_reason(self) -> Optional[AblyException]:
        """An AblyException instance describing the last error which occurred on the channel, if any."""
        return self.__error_reason

    @property
    def params(self) -> Dict[str, str]:
        """Get channel parameters"""
        return self.__params

    def _start_decode_failure_recovery(self, error: AblyException) -> None:
        """Start RTL18 decode failure recovery procedure"""

        if self.__decode_failure_recovery_in_progress:
            log.info('VCDiff recovery process already started, skipping')
            return

        self.__decode_failure_recovery_in_progress = True

        # RTL18a: Log error with code 40018
        log.error(f'VCDiff decode failure: {error}')

        # RTL18b: Message is already discarded by not processing it

        # RTL18c: Send ATTACH with previous channel serial and transition to ATTACHING
        self._notify_state(ChannelState.ATTACHING, reason=error)
        self._check_pending_state()


class Channels(RestChannels):
    """Creates and destroys RealtimeChannel objects.

    Methods
    -------
    get(name)
        Gets a channel
    release(name)
        Releases a channel
    """

    # RTS3
    def get(self, name: str, options: Optional[ChannelOptions] = None) -> RealtimeChannel:
        """Creates a new RealtimeChannel object, or returns the existing channel object.

        Parameters
        ----------

        name: str
            Channel name
        options: ChannelOptions or dict, optional
            Channel options for the channel
        """
        if name not in self.__all:
            channel = self.__all[name] = RealtimeChannel(self.__ably, name, options)
        else:
            channel = self.__all[name]
            # Update options if channel is not attached or currently attaching
            if options and channel.should_reattach_to_set_options(options):
                raise AblyException(
                    'Channels.get() cannot be used to set channel options that would cause the channel to '
                    'reattach. Please, use RealtimeChannel.setOptions() instead.',
                    400,
                    40000
                )
            elif options:
                channel.set_options_without_reattach(options)
        return channel

    # RTS4
    def release(self, name: str) -> None:
        """Releases a RealtimeChannel object, deleting it, and enabling it to be garbage collected

        It also removes any listeners associated with the channel.
        To release a channel, the channel state must be INITIALIZED, DETACHED, or FAILED.


        Parameters
        ----------
        name: str
            Channel name
        """
        if name not in self.__all:
            return
        del self.__all[name]

    def _on_channel_message(self, msg: dict) -> None:
        channel_name = msg.get('channel')
        if not channel_name:
            log.error(
                'Channels.on_channel_message()',
                f'received event without channel, action = {msg.get("action")}'
            )
            return

        channel = self.__all[channel_name]
        if not channel:
            log.warning(
                'Channels.on_channel_message()',
                f'receieved event for non-existent channel: {channel_name}'
            )
            return

        channel._on_message(msg)

    def _propagate_connection_interruption(self, state: ConnectionState, reason: Optional[AblyException]) -> None:
        from_channel_states = (
            ChannelState.ATTACHING,
            ChannelState.ATTACHED,
            ChannelState.DETACHING,
            ChannelState.SUSPENDED,
        )

        connection_to_channel_state = {
            ConnectionState.CLOSING: ChannelState.DETACHED,
            ConnectionState.CLOSED: ChannelState.DETACHED,
            ConnectionState.FAILED: ChannelState.FAILED,
            ConnectionState.SUSPENDED: ChannelState.SUSPENDED,
        }

        for channel_name in self.__all:
            channel = self.__all[channel_name]
            if channel.state in from_channel_states:
                channel._notify_state(connection_to_channel_state[state], reason)

    def _on_connected(self) -> None:
        for channel_name in self.__all:
            channel = self.__all[channel_name]
            if channel.state == ChannelState.ATTACHING or channel.state == ChannelState.DETACHING:
                channel._check_pending_state()
            elif channel.state == ChannelState.SUSPENDED:
                asyncio.create_task(channel.attach())
            elif channel.state == ChannelState.ATTACHED:
                channel._request_state(ChannelState.ATTACHING)

    def _initialize_channels(self) -> None:
        for channel_name in self.__all:
            channel = self.__all[channel_name]
            channel._request_state(ChannelState.INITIALIZED)
