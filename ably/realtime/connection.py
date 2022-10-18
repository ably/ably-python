import functools
import logging
import asyncio
import websockets
import json
from ably.http.httputils import HttpUtils
from ably.util.exceptions import AblyAuthException, AblyException
from enum import Enum, IntEnum
from pyee.asyncio import AsyncIOEventEmitter
from datetime import datetime
from ably.util import helper
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


class ConnectionState(Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
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


class Connection(AsyncIOEventEmitter):
    """Ably Realtime Connection

    Enables the management of a connection to Ably

    Attributes
    ----------
    realtime: any
        Realtime client
    state: str
        Connection state
    connection_manager: ConnectionManager
        Connection manager


    Methods
    -------
    connect()
        Establishes a realtime connection
    close()
        Closes a realtime connection
    ping()
        Pings a realtime connection
    on_state_update(state_change)
        Update and emit current state
    """

    def __init__(self, realtime):
        """Constructs a Connection object.

        Parameters
        ----------
        realtime: any
            Ably realtime client
        """
        self.__realtime = realtime
        self.__state = ConnectionState.CONNECTING if realtime.options.auto_connect else ConnectionState.INITIALIZED
        self.__connection_manager = ConnectionManager(realtime, self.state)
        self.__connection_manager.on('connectionstate', self.on_state_update)
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
        """
        Send a ping to the realtime connection
        """
        return await self.__connection_manager.ping()

    def on_state_update(self, state_change):
        """Update and emit the connection state
        """
        self.__state = state_change.current
        self.__realtime.options.loop.call_soon(functools.partial(self.emit, state_change.current, state_change))

    @property
    def state(self):
        """Returns connection state"""
        return self.__state

    @state.setter
    def state(self, value):
        """Sets connection state"""
        self.__state = value

    @property
    def connection_manager(self):
        """Returns connection manager"""
        return self.__connection_manager


class ConnectionManager(AsyncIOEventEmitter):
    """Ably Realtime Connection

    Attributes
    ----------
    realtime: any
        Ably realtime client
    initial_state: str
        Initial connection state
    ably: any
        Ably object
    state: str
        Connection state


    Methods
    -------
    enact_state_change(state, reason=None)
        Set new state
    connect()
        Establishes a realtime connection
    close()
        Closes a realtime connection
    ping()
        Pings a realtime connection
    connect_impl()
        Send a connection to ably websocket
    send_close_message()
        Send a close protocol message to ably
    send_protocol_message(protocol_message)
        Send protocol message to ably
    setup_ws()
        Set up ably websocket connection
    ws_read_loop()
        Handle response from ably websocket
    """

    def __init__(self, realtime, initial_state):
        """Constructs a Connection object.

        Parameters
        ----------
        realtime: any
            Ably realtime client
        initial_state: any
            Initial connection state
        """
        self.options = realtime.options
        self.__ably = realtime
        self.__state = initial_state
        self.__connected_future = asyncio.Future() if initial_state == ConnectionState.CONNECTING else None
        self.__closed_future = None
        self.__websocket = None
        self.setup_ws_task = None
        self.__ping_future = None
        super().__init__()

    def enact_state_change(self, state, reason=None):
        """Sets new connection state

        Parameters
        ----------
        state: any
            The current connection state
        reason: AblyException, optional
            Error object describing the last error received if a connection failure occurs
        """
        current_state = self.__state
        self.__state = state
        self.emit('connectionstate', ConnectionStateChange(current_state, state, reason))

    async def connect(self):
        """Establishes a realtime connection.

        Explicitly calling connect() is unnecessary unless the autoConnect attribute of the ClientOptions object
        is false. Unless already connected or connecting, this method causes the connection to open, entering the
        CONNECTING state.
        """
        if self.__state == ConnectionState.CONNECTED:
            return

        if self.__state == ConnectionState.CONNECTING:
            if self.__connected_future is None:
                log.fatal('Connection state is CONNECTING but connected_future does not exist')
                return
            await self.__connected_future
            self.enact_state_change(ConnectionState.CONNECTED)
        else:
            self.enact_state_change(ConnectionState.CONNECTING)
            self.__connected_future = asyncio.Future()
            await self.connect_impl()

    async def close(self):
        """Causes the connection to close, entering the closing state.

        Once closed, the library will not attempt to re-establish the
        connection without an explicit call to connect()
        """
        if self.__state != ConnectionState.CONNECTED:
            log.warn('Connection.closed called while connection state not connected')
        self.enact_state_change(ConnectionState.CLOSING)
        self.__closed_future = asyncio.Future()
        if self.__websocket and self.__state != ConnectionState.FAILED:
            await self.send_close_message()
            await self.__closed_future
        else:
            log.warn('Connection.closed called while connection already closed or not established')
        self.enact_state_change(ConnectionState.CLOSED)
        if self.setup_ws_task:
            await self.setup_ws_task

    async def connect_impl(self):
        """Send a connection to ably websocket """
        self.setup_ws_task = self.ably.options.loop.create_task(self.setup_ws())
        await self.__connected_future
        self.enact_state_change(ConnectionState.CONNECTED)

    async def send_close_message(self):
        """Send a close protocol message to ably"""
        await self.send_protocol_message({"action": ProtocolMessageAction.CLOSE})

    async def send_protocol_message(self, protocol_message):
        """Send protocol message to ably"""
        await self.__websocket.send(json.dumps(protocol_message))

    async def setup_ws(self):
        """Set up ably websocket connection

        Raises
        ------
        AblyAuthException
            If connection cannot be established
        """
        headers = HttpUtils.default_headers()
        async with websockets.connect(f'wss://{self.options.realtime_host}?key={self.ably.key}',
                                      extra_headers=headers) as websocket:
            self.__websocket = websocket
            task = self.ably.options.loop.create_task(self.ws_read_loop())
            try:
                await task
            except AblyAuthException:
                return

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
        if self.__ping_future:
            response = await self.__ping_future
            return response

        self.__ping_future = asyncio.Future()
        if self.__state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            self.__ping_id = helper.get_random_id()
            ping_start_time = datetime.now().timestamp()
            await self.send_protocol_message({"action": ProtocolMessageAction.HEARTBEAT,
                                              "id": self.__ping_id})
        else:
            raise AblyException("Cannot send ping request. Calling ping in invalid state", 40000, 400)
        ping_end_time = datetime.now().timestamp()
        response_time_ms = (ping_end_time - ping_start_time) * 1000
        return round(response_time_ms, 2)

    async def ws_read_loop(self):
        """Handle response from ably websocket"""
        while True:
            raw = await self.__websocket.recv()
            msg = json.loads(raw)
            action = msg['action']
            if action == ProtocolMessageAction.CONNECTED:  # CONNECTED
                if self.__connected_future:
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
                        self.__ping_future.set_result(None)
                        self.__ping_future = None
            if action in (
                ProtocolMessageAction.ATTACHED,
                ProtocolMessageAction.DETACHED,
                ProtocolMessageAction.MESSAGE
            ):
                self.ably.channels.on_channel_message(msg)

    @property
    def ably(self):
        """Returns ably client"""
        return self.__ably

    @property
    def state(self):
        """Returns channel state"""
        return self.__state
