from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio
from enum import IntEnum
import json
import logging
import socket
import urllib.parse
from ably.http.httputils import HttpUtils
from ably.transport.defaults import Defaults
from ably.util.exceptions import AblyException
from websockets.client import WebSocketClientProtocol, connect as ws_connect
from websockets.exceptions import ConnectionClosedOK, WebSocketException

if TYPE_CHECKING:
    from ably.realtime.connection import ConnectionManager

log = logging.getLogger(__name__)


class ProtocolMessageAction(IntEnum):
    HEARTBEAT = 0
    CONNECTED = 4
    CLOSE = 7
    CLOSED = 8
    ERROR = 9
    ATTACH = 10
    ATTACHED = 11
    DETACH = 12
    DETACHED = 13
    MESSAGE = 15


class WebSocketTransport:
    def __init__(self, connection_manager: ConnectionManager):
        self.websocket: WebSocketClientProtocol | None = None
        self.read_loop: asyncio.Task | None = None
        self.connect_task: asyncio.Task | None = None
        self.ws_connect_task: asyncio.Task | None = None
        self.connection_manager = connection_manager
        self.is_connected = False

    async def connect(self):
        headers = HttpUtils.default_headers()
        protocol_version = Defaults.protocol_version
        params = {"key": self.connection_manager.ably.key, "v": protocol_version}
        query_params = urllib.parse.urlencode(params)
        ws_url = (f'wss://{self.connection_manager.options.get_realtime_host()}?{query_params}')
        log.info(f'connect(): attempting to connect to {ws_url}')
        self.ws_connect_task = asyncio.create_task(self.ws_connect(ws_url, headers))
        self.ws_connect_task.add_done_callback(self.on_ws_connect_done)

    def on_ws_connect_done(self, task: asyncio.Task):
        try:
            exception = task.exception()
        except asyncio.CancelledError as e:
            exception = e
        if exception is None or isinstance(exception, ConnectionClosedOK):
            return
        connected_future = asyncio.Future()
        connected_future.set_exception(exception)
        self.connection_manager.on_connection_attempt_done(connected_future)

    async def ws_connect(self, ws_url, headers):
        try:
            async with ws_connect(ws_url, extra_headers=headers) as websocket:
                log.info(f'ws_connect(): connection established to {ws_url}')
                self.websocket = websocket
                self.read_loop = self.connection_manager.options.loop.create_task(self.ws_read_loop())
                self.read_loop.add_done_callback(self.on_read_loop_done)
                await self.read_loop
        except (WebSocketException, socket.gaierror) as e:
            raise AblyException(f'Error opening websocket connection: {e}', 400, 40000)

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
                await self.connection_manager.on_protocol_message(msg)
            else:
                raise Exception('ws_read_loop running with no websocket')

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
        if self.websocket:
            try:
                await self.websocket.close()
            except asyncio.CancelledError:
                return

    async def close(self):
        await self.send({'action': ProtocolMessageAction.CLOSE})

    async def send(self, message: dict):
        if self.websocket is None:
            raise Exception()
        raw_msg = json.dumps(message)
        log.info(f'WebSocketTransport.send(): sending {raw_msg}')
        await self.websocket.send(raw_msg)
