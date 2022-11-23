import functools
import logging
import asyncio
import websockets
import json
from ably.http.httputils import HttpUtils
from ably.util.exceptions import AblyAuthException, AblyException
from ably.util.eventemitter import EventEmitter
from enum import Enum, IntEnum
from datetime import datetime
from ably.util import helper
from dataclasses import dataclass
from typing import Optional
from websockets.client import WebSocketClientProtocol, connect as ws_connect
from websockets.exceptions import ConnectionClosedOK

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
    ERROR = 9
    CLOSE = 7
    CLOSED = 8
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
        self.read_loop = None
        self.transport: WebSocketTransport | None = None
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
                exception = AblyException(
                    "Connection cancelled due to request timeout. Attempting reconnection...", 504, 50003)
                self.enact_state_change(ConnectionState.DISCONNECTED, exception)
                log.info('Connection cancelled due to request timeout. Attempting reconnection...')
                raise exception
            self.enact_state_change(ConnectionState.CONNECTED)
        else:
            self.enact_state_change(ConnectionState.CONNECTING)
            self.__connected_future = asyncio.Future()
            await self.connect_impl()

    async def close(self):
        if self.__state in (ConnectionState.CLOSED, ConnectionState.INITIALIZED, ConnectionState.FAILED):
            return
        if self.__state != ConnectionState.CONNECTED:
            log.warning('Connection.closed called while connection state not connected')
        if self.__state == ConnectionState.CONNECTING:
            await self.__connected_future
        self.enact_state_change(ConnectionState.CLOSING)
        self.__closed_future = asyncio.Future()
        if self.transport and self.transport.isConnected:
            await self.transport.close()
        else:
            log.warning('ConnectionManager: called close with no connected transport')
        # if self.__websocket and self.__state != ConnectionState.FAILED:
        #     await self.send_close_message()
        #     try:
        #         await asyncio.wait_for(self.__closed_future, self.__timeout_in_secs)
        #     except asyncio.TimeoutError:
        #         raise AblyException("Timeout waiting for connection close response", 504, 50003)
        # else:
        #     log.warning('Connection.closed called while connection already closed or not established')
        await self.__closed_future
        self.enact_state_change(ConnectionState.CLOSED)
        # if self.setup_ws_task:
        #     await self.setup_ws_task
        if self.transport and self.transport.ws_connect_task is not None:
            await self.transport.ws_connect_task

    def on_setup_ws_done(self, task):
        try:
            exception = task.exception()
        except asyncio.CancelledError as e:
            exception = e

        if exception is not None:
            try:
                self.__connected_future.cancelled()
            except Exception as e:
                print('except!')
            if self.__connected_future and not self.__connected_future.cancelled():
                self.__connected_future.set_exception(exception)
                self.enact_state_change(ConnectionState.DISCONNECTED, exception)

    async def connect_impl(self):
        # self.setup_ws_task = self.__ably.options.loop.create_task(self.setup_ws())
        # self.setup_ws_task.add_done_callback(self.on_setup_ws_done)
        # try:
        #     await asyncio.wait_for(self.__connected_future, self.__timeout_in_secs)
        # except asyncio.TimeoutError:
        #     exception = AblyException("Timeout waiting for realtime connection", 504, 50003)
        #     self.enact_state_change(ConnectionState.DISCONNECTED, exception)
        #     if self.read_loop is not None:
        #         self.read_loop.cancel()
        #         self.read_loop = None
        #     await asyncio.sleep(self.options.disconnected_retry_timeout / 1000)
        #     log.info('Attempting reconnection')
        #     await self.connect()
        # self.enact_state_change(ConnectionState.CONNECTED)
        self.transport = WebSocketTransport(self)
        await self.transport.connect()
        await self.__connected_future
        self.enact_state_change(ConnectionState.CONNECTED)

    async def send_close_message(self):
        await self.send_protocol_message({"action": ProtocolMessageAction.CLOSE})

    async def send_protocol_message(self, protocolMessage):
        if self.transport is not None:
            await self.transport.send(protocolMessage)
        else:
            raise Exception()

    def on_read_loop_done(self, task):
        try:
            exception = task.exception()
        except asyncio.CancelledError as e:
            exception = e

        print(f'on_read_loop_done, exception = {exception}')

    async def setup_ws(self):
        headers = HttpUtils.default_headers()
        ws_url = f'wss://{self.options.get_realtime_host()}?key={self.__ably.key}'
        log.info(f'setup_ws(): attempting to connect to {ws_url}')
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            log.info(f'setup_ws(): connection established to {ws_url}')
            self.__websocket = websocket
            self.read_loop = self.__ably.options.loop.create_task(self.ws_read_loop())
            self.read_loop.add_done_callback(self.on_read_loop_done)
            try:
                await self.read_loop
            except AblyAuthException:
                return
            except Exception:
                return

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
                self.transport.isConnected = True
            if self.__connected_future:
                if not self.__connected_future.cancelled():
                    self.__connected_future.set_result(None)
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
                if self.transport:
                    await self.transport.dispose()
                raise exception
        if action == ProtocolMessageAction.CLOSED:
            # await self.transport.close()
            if self.transport:
                await self.transport.dispose()
            # self.__websocket = None
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


class WebSocketTransport:
    def __init__(self, connection_manager: ConnectionManager):
        self.websocket: WebSocketClientProtocol | None = None
        self.read_loop: asyncio.Task | None = None
        self.connect_task: asyncio.Task | None = None
        self.ws_connect_task: asyncio.Task | None = None
        self.connection_manager = connection_manager
        self.isDisposed = False
        self.isConnected = False
        self.isFinished = False

    async def connect(self):
        headers = HttpUtils.default_headers()
        host = self.connection_manager.options.get_realtime_host()
        key = self.connection_manager.ably.key
        ws_url = f'wss://{host}?key={key}'
        log.info(f'setup_ws(): attempting to connect to {ws_url}')
        self.ws_connect_task = asyncio.create_task(self.ws_connect(ws_url, headers))
        self.ws_connect_task.add_done_callback(self.on_ws_connect_done)

    def on_ws_connect_done(self, task: asyncio.Task):
        try:
            exception = task.exception()
        except asyncio.CancelledError as e:
            exception = e
        if isinstance(exception, ConnectionClosedOK):
            return

    async def ws_connect(self, ws_url, headers):
        async with ws_connect(ws_url, extra_headers=headers) as websocket:
            log.info(f'setup_ws(): connection established to {ws_url}')
            self.websocket = websocket
            self.read_loop = self.connection_manager.options.loop.create_task(self.ws_read_loop())
            self.read_loop.add_done_callback(self.on_read_loop_done)
            await self.read_loop

    async def ws_read_loop(self):
        while True:
            if self.websocket is not None:
                try:
                    raw = await self.websocket.recv()
                except ConnectionClosedOK:
                    break
                msg = json.loads(raw)
                log.info(f'ws_read_loop(): receieved protocol message: {msg}')
                if msg['action'] == ProtocolMessageAction.CLOSED:
                    if self.ws_connect_task:
                        self.ws_connect_task.cancel()
                        # self.ws_connect_task = None
                await self.connection_manager.on_protocol_message(msg)
            else:
                raise Exception()

    def on_read_loop_done(self, task: asyncio.Task):
        try:
            exception = task.exception()
        except asyncio.CancelledError as e:
            exception = e
        if isinstance(exception, ConnectionClosedOK):
            return

    async def dispose(self):
        if self.read_loop:
            self.read_loop.cancel()
        if self.ws_connect_task:
            self.ws_connect_task.cancel()
            # await self.ws_connect_task
        if self.websocket:
            await self.websocket.close()
        pass

    def disconnect(self):
        pass

    async def close(self):
        await self.send({'action': ProtocolMessageAction.CLOSE})

    async def send(self, message: dict):
        if self.websocket is None:
            raise Exception()
        raw_msg = json.dumps(message)
        log.info(f'WebSocketTransport.send(): sending {raw_msg}')
        await self.websocket.send(raw_msg)
