import asyncio
import websockets
import json
from ably.util.exceptions import AblyAuthException
from enum import Enum


class ConnectionState(Enum):
    INITIALIZED = 'initialized'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'


class RealtimeConnection:
    def __init__(self, realtime):
        self.options = realtime.options
        self.__ably = realtime
        self.__state = ConnectionState.INITIALIZED

    async def connect(self):
        self.__state = ConnectionState.CONNECTING
        self.connected_future = asyncio.Future()
        asyncio.create_task(self.connect_impl())
        await self.connected_future
        self.__state = ConnectionState.CONNECTED

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
            if (action == 4): # CONNECTED
                self.connected_future.set_result(None)
            if (action == 9): # ERROR
                error = msg["error"]
                self.connected_future.set_exception(AblyAuthException(error["message"], error["statusCode"], error["code"]))

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self):
        return self.__state
