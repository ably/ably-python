from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio
from enum import IntEnum
import json
import logging
import socket
import urllib.parse
from ably.http.httputils import HttpUtils
from ably.types.connectiondetails import ConnectionDetails
from ably.util.eventemitter import EventEmitter
from ably.util.exceptions import AblyException
from ably.util.helper import Timer, unix_time_ms
from websockets.client import WebSocketClientProtocol, connect as ws_connect
from websockets.exceptions import ConnectionClosedOK, WebSocketException

if TYPE_CHECKING:
    from ably.realtime.connection import ConnectionManager

log = logging.getLogger(__name__)


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


class WebSocketTransport(EventEmitter):
    def __init__(self, connection_manager: ConnectionManager, host: str, params: dict):
        self.websocket: WebSocketClientProtocol | None = None
        self.read_loop: asyncio.Task | None = None
        self.connect_task: asyncio.Task | None = None
        self.ws_connect_task: asyncio.Task | None = None
        self.connection_manager = connection_manager
        self.options = self.connection_manager.options
        self.is_connected = False
        self.idle_timer = None
        self.last_activity = None
        self.max_idle_interval = None
        self.is_disposed = False
        self.host = host
        self.params = params
        super().__init__()

    def connect(self):
        headers = HttpUtils.default_headers()
        query_params = urllib.parse.urlencode(self.params)
        ws_url = (f'wss://{self.host}?{query_params}')
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
        log.info(
            f'WebSocketTransport.on_ws_connect_done(): exception = {exception}'
        )

    async def ws_connect(self, ws_url, headers):
        try:
            async with ws_connect(ws_url, extra_headers=headers) as websocket:
                log.info(f'ws_connect(): connection established to {ws_url}')
                self._emit('connected')
                self.websocket = websocket
                self.read_loop = self.connection_manager.options.loop.create_task(self.ws_read_loop())
                self.read_loop.add_done_callback(self.on_read_loop_done)
                try:
                    await self.read_loop
                except WebSocketException as err:
                    if not self.is_disposed:
                        await self.dispose()
                        self.connection_manager.deactivate_transport(err)
        except (WebSocketException, socket.gaierror) as e:
            exception = AblyException(f'Error opening websocket connection: {e}', 400, 40000)
            log.exception(f'WebSocketTransport.ws_connect(): Error opening websocket connection: {exception}')
            self._emit('failed', exception)
            raise exception

    async def on_protocol_message(self, msg):
        self.on_activity()
        log.info(f'WebSocketTransport.on_protocol_message(): receieved protocol message: {msg}')
        action = msg.get('action')
        if action == ProtocolMessageAction.CONNECTED:
            connection_id = msg.get('connectionId')
            connection_details = ConnectionDetails.from_dict(msg.get('connectionDetails'))

            error = msg.get('error')
            exception = None
            if error:
                exception = AblyException(error.get('message'), error.get('statusCode'), error.get('code'))

            max_idle_interval = connection_details.max_idle_interval
            if max_idle_interval:
                self.max_idle_interval = max_idle_interval + self.options.realtime_request_timeout
                self.on_activity()
            self.is_connected = True
            if self.host != self.options.get_realtime_host():  # RTN17e
                self.options.fallback_realtime_host = self.host
            self.connection_manager.on_connected(connection_details, connection_id, reason=exception)
        elif action == ProtocolMessageAction.DISCONNECTED:
            self.connection_manager.on_disconnected(msg)
        elif action == ProtocolMessageAction.CLOSED:
            if self.ws_connect_task:
                self.ws_connect_task.cancel()
            await self.connection_manager.on_closed()
        elif action == ProtocolMessageAction.ERROR:
            error = msg.get('error')
            exception = AblyException(error.get('message'), error.get('statusCode'), error.get('code'))
            await self.connection_manager.on_error(msg, exception)
        elif action == ProtocolMessageAction.HEARTBEAT:
            id = msg.get('id')
            self.connection_manager.on_heartbeat(id)
        elif action in (
            ProtocolMessageAction.ATTACHED,
            ProtocolMessageAction.DETACHED,
            ProtocolMessageAction.MESSAGE
        ):
            self.connection_manager.on_channel_message(msg)

    async def ws_read_loop(self):
        while True:
            if self.websocket is not None:
                try:
                    raw = await self.websocket.recv()
                except ConnectionClosedOK:
                    break
                msg = json.loads(raw)
                await self.on_protocol_message(msg)
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
        self.is_disposed = True
        if self.read_loop:
            self.read_loop.cancel()
        if self.ws_connect_task:
            self.ws_connect_task.cancel()
        if self.idle_timer:
            self.idle_timer.cancel()
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

    def set_idle_timer(self, timeout: float):
        if not self.idle_timer:
            self.idle_timer = Timer(timeout, self.on_idle_timer_expire)

    async def on_idle_timer_expire(self):
        self.idle_timer = None
        since_last = unix_time_ms() - self.last_activity
        time_remaining = self.max_idle_interval - since_last
        msg = f"No activity seen from realtime in {since_last} ms; assuming connection has dropped"
        if time_remaining <= 0:
            log.error(msg)
            await self.disconnect(AblyException(msg, 408, 80003))
        else:
            self.set_idle_timer(time_remaining + 100)

    def on_activity(self):
        if not self.max_idle_interval:
            return
        self.last_activity = unix_time_ms()
        self.set_idle_timer(self.max_idle_interval + 100)

    async def disconnect(self, reason=None):
        await self.dispose()
        self.connection_manager.deactivate_transport(reason)