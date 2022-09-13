import asyncio
import websockets
import json


class RealtimeConnection:
    def __init__(self, realtime):
        self.options = realtime.options
        self.__ably = realtime

    async def connect(self):
        self.connected_future = asyncio.Future()
        asyncio.create_task(self.connect_impl())
        return await self.connected_future

    async def connect_impl(self):
        async with websockets.connect(f'wss://realtime.ably.io?key={self.ably.key}') as websocket:
            self.websocket = websocket
            task = asyncio.create_task(self.ws_read_loop())
            await task

    async def ws_read_loop(self):
        while True:
            raw = await self.websocket.recv()
            msg = json.loads(raw)
            action = msg['action']
            if (action == 4): # CONNECTED
                self.connected_future.set_result(msg)
                return msg

    @property
    def ably(self):
        return self.__ably
