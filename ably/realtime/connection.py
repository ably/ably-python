import functools
import logging
import asyncio
import httpx
from ably.realtime.websockettransport import WebSocketTransport, ProtocolMessageAction
from ably.transport.defaults import Defaults
from ably.util.exceptions import AblyException
from ably.util.eventemitter import EventEmitter
from enum import Enum
from datetime import datetime
from ably.util import helper
from dataclasses import dataclass
from typing import Optional
from ably.types.connectiondetails import ConnectionDetails

log = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    CLOSING = 'closing'
    CLOSED = 'closed'
    FAILED = 'failed'
    SUSPENDED = 'suspended'


class ConnectionEvent(str, Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    CLOSING = 'closing'
    CLOSED = 'closed'
    FAILED = 'failed'
    SUSPENDED = 'suspended'
    UPDATE = 'update'


@dataclass
class ConnectionStateChange:
    previous: ConnectionState
    current: ConnectionState
    event: ConnectionEvent
    reason: Optional[AblyException] = None  # RTN4f


class Connection(EventEmitter):  # RTN4
    """Ably Realtime Connection

    Enables the management of a connection to Ably

    Attributes
    ----------
    state: str
        Connection state
    error_reason: ErrorInfo
        An ErrorInfo object describing the last error which occurred on the channel, if any.


    Methods
    -------
    connect()
        Establishes a realtime connection
    close()
        Closes a realtime connection
    ping()
        Pings a realtime connection
    """

    def __init__(self, realtime):
        self.__realtime = realtime
        self.__error_reason = None
        self.__state = ConnectionState.CONNECTING if realtime.options.auto_connect else ConnectionState.INITIALIZED
        self.__connection_manager = ConnectionManager(self.__realtime, self.state)
        self.__connection_manager.on('connectionstate', self._on_state_update)  # RTN4a
        self.__connection_manager.on('update', self._on_connection_update)  # RTN4h
        super().__init__()

    # RTN11
    async def connect(self):
        """Establishes a realtime connection.

        Causes the connection to open, entering the connecting state
        """
        self.__error_reason = None
        await self.__connection_manager.connect()

    async def close(self):
        """Causes the connection to close, entering the closing state.

        Once closed, the library will not attempt to re-establish the
        connection without an explicit call to connect()
        """
        await self.__connection_manager.close()

    # RTN13
    async def ping(self):
        """Send a ping to the realtime connection

        When connected, sends a heartbeat ping to the Ably server and executes
        the callback with any error and the response time in milliseconds when
        a heartbeat ping request is echoed from the server.

        Raises
        ------
        AblyException
            If ping request cannot be sent due to invalid state

        Returns
        -------
        float
            The response time in milliseconds
        """
        return await self.__connection_manager.ping()

    def _on_state_update(self, state_change):
        log.info(f'Connection state changing from {self.state} to {state_change.current}')
        self.__state = state_change.current
        self.__error_reason = state_change.reason
        self.__realtime.options.loop.call_soon(functools.partial(self._emit, state_change.current, state_change))

    def _on_connection_update(self, state_change):
        self.__realtime.options.loop.call_soon(functools.partial(self._emit, ConnectionEvent.UPDATE, state_change))

    # RTN4d
    @property
    def state(self):
        """The current connection state of the connection"""
        return self.__state

    # RTN25
    @property
    def error_reason(self):
        """An object describing the last error which occurred on the channel, if any."""
        return self.__error_reason

    @state.setter
    def state(self, value):
        self.__state = value

    @property
    def connection_manager(self):
        return self.__connection_manager

    @property
    def connection_details(self):
        return self.__connection_manager.connection_details


class ConnectionManager(EventEmitter):
    def __init__(self, realtime, initial_state):
        self.options = realtime.options
        self.__ably = realtime
        self.__state = initial_state
        self.__connected_future = asyncio.Future() if initial_state == ConnectionState.CONNECTING else None
        self.__closed_future = None
        self.__ping_future = None
        self.__timeout_in_secs = self.options.realtime_request_timeout / 1000
        self.retry_connection_attempt_task = None
        self.connection_attempt_task = None
        self.transport: WebSocketTransport | None = None
        self.__ttl_task = None
        self.__connection_details = None
        self.__fail_state = ConnectionState.DISCONNECTED
        self.__connection_host = self.options.get_realtime_host()
        self.__fallback_hosts = self.__generate_fallback_hosts()
        super().__init__()

    def enact_state_change(self, state, reason=None):
        current_state = self.__state
        self.__state = state
        if self.__state == ConnectionState.DISCONNECTED:
            if not self.__ttl_task or self.__ttl_task.done():
                self.__ttl_task = asyncio.create_task(self.__start_suspended_timer())
        self._emit('connectionstate', ConnectionStateChange(current_state, state, state, reason))

    async def __start_suspended_timer(self):
        if self.__connection_details:
            self.ably.options.connection_state_ttl = self.__connection_details.connection_state_ttl
        await asyncio.sleep(self.ably.options.connection_state_ttl / 1000)
        exception = AblyException("Exceeded connectionStateTtl while in DISCONNECTED state", 504, 50003)  # RTN14e
        self.enact_state_change(ConnectionState.SUSPENDED, exception)
        self.__connection_details = None
        self.__fail_state = ConnectionState.SUSPENDED

    async def connect(self):
        if not self.__connected_future:
            self.__connected_future = asyncio.Future()
            self.try_connect()
        await self.__connected_future

    def try_connect(self):
        self.connection_attempt_task = asyncio.create_task(self._connect())
        self.connection_attempt_task.add_done_callback(self.on_connection_attempt_done)

    def __generate_fallback_hosts(self):
        for host in self.options.get_fallback_realtime_hosts():
            yield host

    def __use_fallback_host(self):
        try:
            self.__connection_host = next(self.__fallback_hosts)
        except StopIteration as e:
            log.warning("Exhausted Fallback hosts", {e})
            return


    async def _connect(self):
        if self.__state == ConnectionState.CONNECTED:
            return

        if self.__state == ConnectionState.CONNECTING:
            try:
                if not self.__connected_future:
                    self.__connected_future = asyncio.Future()
                await self.__connected_future
            except asyncio.CancelledError:
                exception = AblyException(
                    "Connection cancelled due to request timeout. Attempting reconnection...", 504, 50003)
                log.info('Connection cancelled due to request timeout. Attempting reconnection...')
                raise exception
        else:
            self.enact_state_change(ConnectionState.CONNECTING)
            await self.connect_impl()

    def check_connection(self):
        try:
            response = httpx.get(self.options.connectivity_check_url)
            return 200 <= response.status_code < 300 and \
                (self.options.connectivity_check_url != Defaults.connectivity_check_url or "yes" in response.text)
        except httpx.HTTPError:
            return False

    def on_connection_attempt_done(self, task):
        if self.connection_attempt_task:
            if not self.connection_attempt_task.done():
                self.connection_attempt_task.cancel()
            self.connection_attempt_task = None
        if self.retry_connection_attempt_task:
            if not self.retry_connection_attempt_task.done():
                self.retry_connection_attempt_task.cancel()
            self.retry_connection_attempt_task = None
        try:
            exception = task.exception()
        except asyncio.CancelledError:
            exception = AblyException(
                "Connection cancelled due to request timeout. Attempting reconnection...", 504, 50003)
        if exception is None:
            return
        if self.__state in (ConnectionState.CLOSED, ConnectionState.FAILED):
            return
        if self.__state != ConnectionState.DISCONNECTED:
            if self.__connected_future:
                self.__connected_future.set_exception(exception)
                self.__connected_future = None
            self.enact_state_change(ConnectionState.DISCONNECTED, exception)  # RTN14d
        self.retry_connection_attempt_task = asyncio.create_task(self.retry_connection_attempt())

    async def retry_connection_attempt(self):
        if self.__fail_state == ConnectionState.SUSPENDED:
            retry_timeout = self.ably.options.suspended_retry_timeout / 1000
        else:
            retry_timeout = self.ably.options.disconnected_retry_timeout / 1000
        await asyncio.sleep(retry_timeout)
        if self.check_connection():
            self.try_connect()
        else:
            exception = AblyException("Unable to connect (network unreachable)", 80003, 404)
            self.enact_state_change(self.__fail_state, exception)

    async def close(self):
        if self.__state in (ConnectionState.CLOSED, ConnectionState.INITIALIZED, ConnectionState.FAILED):
            self.enact_state_change(ConnectionState.CLOSED)
            return
        if self.__state is ConnectionState.DISCONNECTED:
            if self.transport:
                await self.transport.dispose()
                self.transport = None
                self.enact_state_change(ConnectionState.CLOSED)
                return
        if self.__state != ConnectionState.CONNECTED:
            log.warning('Connection.closed called while connection state not connected')
        if self.__state == ConnectionState.CONNECTING:
            await self.__connected_future
        self.enact_state_change(ConnectionState.CLOSING)
        self.__closed_future = asyncio.Future()
        if self.transport and self.transport.is_connected:
            await self.transport.close()
            try:
                await asyncio.wait_for(self.__closed_future, self.__timeout_in_secs)
            except asyncio.TimeoutError:
                raise AblyException("Timeout waiting for connection close response", 504, 50003)
        else:
            log.warning('ConnectionManager: called close with no connected transport')
        self.enact_state_change(ConnectionState.CLOSED)
        if self.__ttl_task and not self.__ttl_task.done():
            self.__ttl_task.cancel()
        if self.transport and self.transport.ws_connect_task is not None:
            try:
                await self.transport.ws_connect_task
            except AblyException as e:
                log.warning(f'Connection error encountered while closing: {e}')

    async def connect_impl(self):
        self.transport = WebSocketTransport(self)  # RTN1
        self._emit('transport.pending', self.transport)
        await self.transport.connect(self.__connection_host)
        try:
            await asyncio.wait_for(asyncio.shield(self.__connected_future), self.__timeout_in_secs)
        except asyncio.TimeoutError:
            exception = AblyException("Timeout waiting for realtime connection", 504, 50003)  # RTN14c
            if self.transport:
                await self.transport.dispose()
                self.tranpsort = None
            self.__connected_future.set_exception(exception)
            connected_future = self.__connected_future
            self.__connected_future = None
            self.__use_fallback_host()
            self.on_connection_attempt_done(connected_future)

    async def send_protocol_message(self, protocol_message):
        if self.transport is not None:
            await self.transport.send(protocol_message)
        else:
            raise Exception()

    async def ping(self):
        if self.__ping_future:
            try:
                response = await self.__ping_future
            except asyncio.CancelledError:
                raise AblyException("Ping request cancelled due to request timeout", 504, 50003)
            return response

        self.__ping_future = asyncio.Future()
        if self.__state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            self.__ping_id = helper.get_random_id()
            ping_start_time = datetime.now().timestamp()
            await self.send_protocol_message({"action": ProtocolMessageAction.HEARTBEAT,
                                              "id": self.__ping_id})
        else:
            raise AblyException("Cannot send ping request. Calling ping in invalid state", 40000, 400)
        try:
            await asyncio.wait_for(self.__ping_future, self.__timeout_in_secs)
        except asyncio.TimeoutError:
            raise AblyException("Timeout waiting for ping response", 504, 50003)

        ping_end_time = datetime.now().timestamp()
        response_time_ms = (ping_end_time - ping_start_time) * 1000
        return round(response_time_ms, 2)

    def on_connected(self, connection_details: ConnectionDetails):
        if self.transport:
            self.transport.is_connected = True
        if self.__connected_future:
            if not self.__connected_future.cancelled():
                self.__connected_future.set_result(None)
            self.__connected_future = None
        self.__fail_state = ConnectionState.DISCONNECTED
        if self.__ttl_task:
            self.__ttl_task.cancel()
        self.__connection_details = connection_details  # RTN21
        if self.__state == ConnectionState.CONNECTED:  # RTN24
            state_change = ConnectionStateChange(ConnectionState.CONNECTED, ConnectionState.CONNECTED,
                                                 ConnectionEvent.UPDATE)
            self._emit(ConnectionEvent.UPDATE, state_change)
        else:
            self.enact_state_change(ConnectionState.CONNECTED)

    async def on_error(self, msg: dict, exception: AblyException):
        if msg.get('channel') is None:  # RTN15i
            self.enact_state_change(ConnectionState.FAILED, exception)
            if self.__connected_future:
                self.__connected_future.set_exception(exception)
                self.__connected_future = None
            if self.transport:
                await self.transport.dispose()
            raise exception

    async def on_closed(self):
        if self.transport:
            await self.transport.dispose()
        if self.__closed_future and not self.__closed_future.done():
            self.__closed_future.set_result(None)

    def on_channel_message(self, msg: dict):
        self.__ably.channels._on_channel_message(msg)

    def on_heartbeat(self, id: Optional[str]):
        if self.__ping_future:
            # Resolve on heartbeat from ping request.
            if self.__ping_id == id:
                if not self.__ping_future.cancelled():
                    self.__ping_future.set_result(None)
                self.__ping_future = None

    def deactivate_transport(self, reason=None):
        self.transport = None
        self.enact_state_change(ConnectionState.DISCONNECTED, reason)

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self):
        return self.__state

    @property
    def connection_details(self):
        return self.__connection_details
