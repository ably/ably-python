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

log = logging.getLogger(__name__)


class ConnectionState(Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    CLOSING = 'closing'
    CLOSED = 'closed'
    FAILED = 'failed'


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


class Connection(AsyncIOEventEmitter):
    def __init__(self, realtime):
        self.__realtime = realtime
        self.__connection_manager = ConnectionManager(realtime)
        self.__connection_manager = ConnectionManager(realtime, self.state)
        self.__connection_manager.on('connectionstate', self.on_state_update)
        super().__init__()

    async def connect(self):
        await self.__connection_manager.connect()

    async def close(self):
        await self.__connection_manager.close()

    async def ping(self):
        return await self.__connection_manager.ping()

    def on_state_update(self, state):
        self.__state = state
        self.__realtime.options.loop.call_soon(functools.partial(self.emit, state))

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, value):
        self.__state = value

    @property
    def connection_manager(self):
        return self.__connection_manager


class ConnectionManager(AsyncIOEventEmitter):
    def __init__(self, realtime, initial_state):
        self.options = realtime.options
        self.__ably = realtime
        self.__state = initial_state
        self.__connected_future = None
        self.__closed_future = None
        self.__websocket = None
        self.setup_ws_task = None
        self.__ping_future = None
        super().__init__()

    def enact_state_change(self, state):
        self.__state = state
        self.emit('connectionstate', state)

    async def connect(self):
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
        self.setup_ws_task = self.ably.options.loop.create_task(self.setup_ws())
        await self.__connected_future
        self.enact_state_change(ConnectionState.CONNECTED)

    async def send_close_message(self):
        await self.sendProtocolMessage({"action": ProtocolMessageAction.CLOSE})

    async def sendProtocolMessage(self, protocolMessage):
        await self.__websocket.send(json.dumps(protocolMessage))

    async def setup_ws(self):
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
        if self.__ping_future:
            response = await self.__ping_future
            return response

        self.__ping_future = asyncio.Future()
        if self.__state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            self.__ping_id = helper.get_random_id()
            ping_start_time = datetime.now().timestamp()
            await self.sendProtocolMessage({"action": ProtocolMessageAction.HEARTBEAT,
                                            "id": self.__ping_id})
        else:
            raise AblyException("Cannot send ping request. Calling ping in invalid state", 40000, 400)
        ping_end_time = datetime.now().timestamp()
        response_time_ms = (ping_end_time - ping_start_time) * 1000
        return round(response_time_ms, 2)

    async def ws_read_loop(self):
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
                    self.enact_state_change(ConnectionState.FAILED)
                    exception = AblyAuthException(error["message"], error["statusCode"], error["code"])
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
            if action in [ProtocolMessageAction.ATTACHED, ProtocolMessageAction.DETACHED]:
                self.ably.channels.on_channel_message(msg)

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self):
        return self.__state
