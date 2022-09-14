import logging
import asyncio
import websockets
import json
from ably.util.exceptions import AblyAuthException
from enum import Enum

log = logging.getLogger(__name__)


class ConnectionState(Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    CLOSING = 'closing'
    CLOSED = 'closed'


class RealtimeConnection:
    def __init__(self, realtime):
        self.options = realtime.options
        self.__ably = realtime
        self.__state = ConnectionState.INITIALIZED
        self.connected_future = None
        self.websocket = None

    async def connect(self):
        if self.__state == ConnectionState.CONNECTED:
            return

        if self.__state == ConnectionState.CONNECTING:
            if self.connected_future is None:
                log.fatal('Connection state is CONNECTING but connected_future does not exits')
                return
            await self.connected_future
        else:
            self.__state = ConnectionState.CONNECTING
            self.connected_future = asyncio.Future()
            asyncio.create_task(self.connect_impl())
            await self.connected_future
            self.__state = ConnectionState.CONNECTED

    async def close(self):
        self.__state = ConnectionState.CLOSING
        if self.websocket:
            await self.websocket.close()
        else:
            log.warn('Connection.closed called while connection already closed')
        self.__state = ConnectionState.CLOSED

    async def connect_impl(self):
        async with websockets.connect(f'wss://{self.options.realtime_host}?key={self.ably.key}') as websocket:
            self.websocket = websocket
            task = asyncio.create_task(self.ws_read_loop())
            await task

    async def ws_read_loop(self):
        while True:
            raw = await self.websocket.recv()
            msg = json.loads(raw)
            action = msg['action']
            if action == 4:  # CONNECTED
                if self.connected_future:
                    self.connected_future.set_result(None)
                    self.connected_future = None
                else:
                    log.warn('CONNECTED message receieved but connected_future not set')
            if action == 9:  # ERROR
                error = msg["error"]
                if error['nonfatal'] is False:
                    if self.connected_future:
                        self.connected_future.set_exception(
                            AblyAuthException(error["message"], error["statusCode"], error["code"]))
                        self.connected_future = None

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self):
        return self.__state
