import functools
import logging
import asyncio
import websockets
import json
import socket
from ably.http.httputils import HttpUtils
from ably.util.exceptions import AblyAuthException, AblyException
from ably.util.eventemitter import EventEmitter
from enum import Enum, IntEnum
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


@dataclass
class ConnectionStateChange:
    previous: ConnectionState
    current: ConnectionState
    reason: Optional[AblyException] = None


class ProtocolMessageAction(IntEnum):
    HEARTBEAT = 0
    CONNECTED = 4
    DISCONNECTED = 6
    CLOSE = 7
    CLOSED = 8
    ERROR = 9
    ATTACH = 10
    ATTACHED = 11
    DETACH = 12
    DETACHED = 13
    MESSAGE = 15


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


class ConnectionManager(EventEmitter):
    def __init__(self, realtime, initial_state):
        self.options = realtime.options
        self.__ably = realtime
        self.__state = initial_state
        self.__connected_future = asyncio.Future() if initial_state == ConnectionState.CONNECTING else None
        self.__closed_future = None
        self.__websocket = None
        self.setup_ws_task = None
        self.__ping_future = None
        self.__timeout_in_secs = self.options.realtime_request_timeout / 1000
        super().__init__()

    def enact_state_change(self, state, reason=None):
        current_state = self.__state
        self.__state = state
        self._emit('connectionstate', ConnectionStateChange(current_state, state, reason))

    async def connect(self):
        if self.__state == ConnectionState.CONNECTED:
            return

        if self.__state == ConnectionState.CONNECTING:
            if self.__connected_future is None:
                log.fatal('Connection state is CONNECTING but connected_future does not exist')
                return
            try:
                await self.__connected_future
            except asyncio.CancelledError:
                exception = AblyException("Connection cancelled due to request timeout", 504, 50003)
                self.enact_state_change(ConnectionState.DISCONNECTED, exception)
                raise exception
            self.enact_state_change(ConnectionState.CONNECTED)
        else:
            self.enact_state_change(ConnectionState.CONNECTING)
            self.__connected_future = asyncio.Future()
            await self.connect_impl()

    async def close(self):
        if self.__state != ConnectionState.CONNECTED:
            log.warning('Connection.closed called while connection state not connected')
        self.enact_state_change(ConnectionState.CLOSING)
        self.__closed_future = asyncio.Future()
        if self.__websocket and self.__state != ConnectionState.FAILED:
            await self.send_close_message()
            try:
                await asyncio.wait_for(self.__closed_future, self.__timeout_in_secs)
            except asyncio.TimeoutError:
                raise AblyException("Timeout waiting for connection close response", 504, 50003)
        else:
            log.warning('Connection.closed called while connection already closed or not established')
        self.enact_state_change(ConnectionState.CLOSED)
        if self.setup_ws_task:
            await self.setup_ws_task

    def on_setup_ws_done(self, task):
        exception = task.exception()
        if exception is not None:
            if self.__connected_future:
                self.__connected_future.set_exception(exception)

    async def connect_impl(self):
        self.setup_ws_task = self.__ably.options.loop.create_task(self.setup_ws())
        self.setup_ws_task.add_done_callback(self.on_setup_ws_done)
        try:
            await asyncio.wait_for(self.__connected_future, self.__timeout_in_secs)
        except asyncio.TimeoutError:
            exception = AblyException("Timeout waiting for realtime connection", 504, 50003)
            self.enact_state_change(ConnectionState.DISCONNECTED, exception)
            raise exception
        self.enact_state_change(ConnectionState.CONNECTED)

    async def send_close_message(self):
        await self.send_protocol_message({"action": ProtocolMessageAction.CLOSE})

    async def send_protocol_message(self, protocolMessage):
        raw_msg = json.dumps(protocolMessage)
        log.info('send_protocol_message(): sending {raw_msg}')
        await self.__websocket.send(raw_msg)

    async def setup_ws(self):
        headers = HttpUtils.default_headers()
        ws_url = f'wss://{self.options.get_realtime_host()}?key={self.__ably.key}'
        log.info(f'setup_ws(): attempting to connect to {ws_url}')
        try:
            async with websockets.connect(ws_url, extra_headers=headers) as websocket:
                log.info(f'setup_ws(): connection established to {ws_url}')
                self.__websocket = websocket
                task = self.__ably.options.loop.create_task(self.ws_read_loop())
                try:
                    await task
                except AblyAuthException:
                    return
        except (websockets.exceptions.WebSocketException, socket.gaierror) as e:
            raise AblyException(f'Error opening websocket connection: {e.message}', 400, 40000)

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

    async def ws_read_loop(self):
        while True:
            raw = await self.__websocket.recv()
            msg = json.loads(raw)
            log.info(f'ws_read_loop(): receieved protocol message: {msg}')
            action = msg['action']
            if action == ProtocolMessageAction.CONNECTED:  # CONNECTED
                if self.__connected_future:
                    if not self.__connected_future.cancelled():
                        self.__connected_future.set_result(None)
                    self.__connected_future = None
                else:
                    log.warn('CONNECTED message received but connected_future not set')
            if action == ProtocolMessageAction.DISCONNECTED:
                exception = AblyException.from_exception(msg.get('error'))
                self.enact_state_change(ConnectionState.DISCONNECTED, exception)
                if self.__connected_future:
                    if not self.__connected_future.cancelled():
                        self.__connected_future.set_result(exception)
                    self.__connected_future = None
                else:
                    log.warn('CONNECTED message received but connected_future not set')
            if action == ProtocolMessageAction.ERROR:  # ERROR
                error = msg["error"]
                if error['nonfatal'] is False:
                    exception = AblyAuthException(error["message"], error["statusCode"], error["code"])
                    self.enact_state_change(ConnectionState.FAILED, exception)
                    if self.__connected_future:
                        self.__connected_future.set_exception(exception)
                        self.__connected_future = None
                    self.__websocket = None
                    raise exception
            if action == ProtocolMessageAction.CLOSED:
                await self.__websocket.close()
                self.__websocket = None
                self.__closed_future.set_result(None)
                break
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
