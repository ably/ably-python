import functools
import logging
import asyncio
import httpx
from ably.realtime.websockettransport import WebSocketTransport, ProtocolMessageAction
from ably.util.exceptions import AblyAuthException, AblyException
from ably.util.eventemitter import EventEmitter
from enum import Enum
from datetime import datetime
from ably.util import helper
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    CLOSING = 'closing'
    CLOSED = 'closed'
    FAILED = 'failed'
    SUSPENDED = "suspended"


@dataclass
class ConnectionStateChange:
    previous: ConnectionState
    current: ConnectionState
    reason: Optional[AblyException] = None


@dataclass
class ConnectionDetails:
    connectionStateTtl: int

    def __init__(self, connection_state_ttl: int):
        self.connectionStateTtl = connection_state_ttl

    @staticmethod
    def from_dict(json_dict: dict):
        return ConnectionDetails(json_dict.get('connectionStateTtl'))


class Connection(EventEmitter):
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
        self.__connection_manager.on('connectionstate', self._on_state_update)
        super().__init__()

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

    @property
    def state(self):
        """The current connection state of the connection"""
        return self.__state

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
        self.transport: WebSocketTransport | None = None
        self.__ttl_task = None
        self.__retry_task = None
        self.__connection_details = None
        self.__fail_state = ConnectionState.DISCONNECTED
        super().__init__()

    def enact_state_change(self, state, reason=None):
        current_state = self.__state
        self.__state = state
        if self.__state == ConnectionState.DISCONNECTED:
            if not self.__ttl_task or self.__ttl_task.done():
                self.__ttl_task = asyncio.create_task(self.__start_suspended_timer())
        self._emit('connectionstate', ConnectionStateChange(current_state, state, reason))

    async def __start_suspended_timer(self):
        if self.__connection_details:
            self.ably.options.connection_state_ttl = self.__connection_details.connectionStateTtl
        await asyncio.sleep(self.ably.options.connection_state_ttl / 1000)
        exception = AblyException("Exceeded connectionStateTtl while in DISCONNECTED state", 504, 50003)
        self.enact_state_change(ConnectionState.SUSPENDED, exception)
        self.__connection_details = None
        self.__fail_state = ConnectionState.SUSPENDED
        if self.__retry_task:
            self.__retry_task.cancel()
            self.__retry_task = asyncio.create_task(self.retry_connection_attempt())

    async def connect(self):
        if not self.__connected_future:
            self.__connected_future = asyncio.Future()
            self.try_connect()
        await self.__connected_future

    def try_connect(self):
        task = asyncio.create_task(self._connect())
        task.add_done_callback(self.on_connection_attempt_done)

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
            response = httpx.get("https://internet-up.ably-realtime.com/is-the-internet-up.txt")
            return response.status_code == 200 and "yes" in response.text
        finally:
            return False

    def on_connection_attempt_done(self, task):
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
            self.enact_state_change(self.__fail_state, exception)
        self.__retry_task = asyncio.create_task(self.retry_connection_attempt())

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
            self.enact_state_change(ConnectionState.FAILED, exception)

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
        self.transport = WebSocketTransport(self)
        await self.transport.connect()
        try:
            await asyncio.wait_for(asyncio.shield(self.__connected_future), self.__timeout_in_secs)
        except asyncio.TimeoutError:
            exception = AblyException("Timeout waiting for realtime connection", 504, 50003)
            if self.transport:
                await self.transport.dispose()
                self.tranpsort = None
            self.__connected_future.set_exception(exception)
            connected_future = self.__connected_future
            self.__connected_future = None
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

    async def on_protocol_message(self, msg):
        action = msg['action']
        if action == ProtocolMessageAction.CONNECTED:  # CONNECTED
            if self.transport:
                self.transport.is_connected = True
            if self.__connected_future:
                if not self.__connected_future.cancelled():
                    self.__connected_future.set_result(None)
                self.__connected_future = None
            else:
                log.warn('CONNECTED message received but connected_future not set')
            self.__fail_state == ConnectionState.DISCONNECTED
            if self.__ttl_task:
                self.__ttl_task.cancel()
            self.__connection_details = ConnectionDetails.from_dict(msg["connectionDetails"])
            self.enact_state_change(ConnectionState.CONNECTED)
        if action == ProtocolMessageAction.ERROR:  # ERROR
            error = msg["error"]
            if error['nonfatal'] is False:
                exception = AblyAuthException(error["message"], error["statusCode"], error["code"])
                self.enact_state_change(ConnectionState.FAILED, exception)
                if self.__connected_future:
                    self.__connected_future.set_exception(exception)
                    self.__connected_future = None
                if self.transport:
                    await self.transport.dispose()
                raise exception
        if action == ProtocolMessageAction.CLOSED:
            if self.transport:
                await self.transport.dispose()
            self.__closed_future.set_result(None)
        if action == ProtocolMessageAction.HEARTBEAT:
            if self.__ping_future:
                # Resolve on heartbeat from ping request.
                # TODO: Handle Normal heartbeat if required
                if self.__ping_id == msg.get("id"):
                    if not self.__ping_future.cancelled():
                        self.__ping_future.set_result(None)
                    self.__ping_future = None
        if action in (
            ProtocolMessageAction.ATTACHED,
            ProtocolMessageAction.DETACHED,
            ProtocolMessageAction.MESSAGE
        ):
            self.__ably.channels._on_channel_message(msg)

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self):
        return self.__state

    @property
    def connection_details(self):
        return self.__connection_details
