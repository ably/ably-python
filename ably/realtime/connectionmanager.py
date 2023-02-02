import logging
import asyncio
import httpx
from ably.transport.websockettransport import WebSocketTransport, ProtocolMessageAction
from ably.transport.defaults import Defaults
from ably.types.connectionstate import ConnectionEvent, ConnectionState, ConnectionStateChange
from ably.util.exceptions import AblyException
from ably.util.eventemitter import EventEmitter
from datetime import datetime
from ably.util.helper import get_random_id, Timer
from typing import Optional
from ably.types.connectiondetails import ConnectionDetails
from queue import Queue

log = logging.getLogger(__name__)


class ConnectionManager(EventEmitter):
    def __init__(self, realtime, initial_state):
        self.options = realtime.options
        self.__ably = realtime
        self.__state = initial_state
        self.__ping_future = None
        self.__timeout_in_secs = self.options.realtime_request_timeout / 1000
        self.transport: WebSocketTransport | None = None
        self.__connection_details = None
        self.connection_id = None
        self.__fail_state = ConnectionState.DISCONNECTED
        self.transition_timer: Timer | None = None
        self.suspend_timer: Timer | None = None
        self.retry_timer: Timer | None = None
        self.connect_base_task: asyncio.Task | None = None
        self.disconnect_transport_task: asyncio.Task | None = None
        self.__fallback_hosts = self.options.get_fallback_realtime_hosts()
        self.queued_messages = Queue()
        super().__init__()

    def enact_state_change(self, state, reason=None):
        current_state = self.__state
        log.info(f'ConnectionManager.enact_state_change(): {current_state} -> {state}')
        self.__state = state
        self._emit('connectionstate', ConnectionStateChange(current_state, state, state, reason))

    def check_connection(self):
        try:
            response = httpx.get(self.options.connectivity_check_url)
            return 200 <= response.status_code < 300 and \
                (self.options.connectivity_check_url != Defaults.connectivity_check_url or "yes" in response.text)
        except httpx.HTTPError:
            return False

    def __get_transport_params(self):
        protocol_version = Defaults.protocol_version
        params = {"key": self.__ably.key, "v": protocol_version}
        if self.connection_details:
            params["resume"] = self.connection_details.connection_key
        return params

    async def close_impl(self):
        log.debug('ConnectionManager.close_impl()')

        self.cancel_suspend_timer()
        self.start_transition_timer(ConnectionState.CLOSING, fail_state=ConnectionState.CLOSED)
        if self.transport:
            await self.transport.dispose()
        if self.connect_base_task:
            self.connect_base_task.cancel()
        if self.disconnect_transport_task:
            await self.disconnect_transport_task
        self.cancel_retry_timer()

        self.notify_state(ConnectionState.CLOSED)

    async def send_protocol_message(self, protocol_message):
        if self.state in (
            ConnectionState.DISCONNECTED,
            ConnectionState.CONNECTING,
        ):
            self.queued_messages.put(protocol_message)
            return

        if self.state == ConnectionState.CONNECTED:
            if self.transport:
                await self.transport.send(protocol_message)
            else:
                log.exception(
                    "ConnectionManager.send_protocol_message(): can not send message with no active transport"
                )
            return

        raise AblyException(f"ConnectionManager.send_protocol_message(): called in {self.state}", 500, 50000)

    def send_queued_messages(self):
        log.info(f'ConnectionManager.send_queued_messages(): sending {self.queued_messages.qsize()} message(s)')
        while not self.queued_messages.empty():
            asyncio.create_task(self.send_protocol_message(self.queued_messages.get()))

    def fail_queued_messages(self, err):
        log.info(
            f"ConnectionManager.fail_queued_messages(): discarding {self.queued_messages.qsize()} messages;" +
            f" reason = {err}"
        )
        while not self.queued_messages.empty():
            msg = self.queued_messages.get()
            log.exception(f"ConnectionManager.fail_queued_messages(): Failed to send protocol message: {msg}")

    async def ping(self):
        if self.__ping_future:
            try:
                response = await self.__ping_future
            except asyncio.CancelledError:
                raise AblyException("Ping request cancelled due to request timeout", 504, 50003)
            return response

        self.__ping_future = asyncio.Future()
        if self.__state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            self.__ping_id = get_random_id()
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

    def on_connected(self, connection_details: ConnectionDetails, connection_id: str, reason=None):
        self.__fail_state = ConnectionState.DISCONNECTED

        self.__connection_details = connection_details
        self.connection_id = connection_id

        if self.__state == ConnectionState.CONNECTED:
            state_change = ConnectionStateChange(ConnectionState.CONNECTED, ConnectionState.CONNECTED,
                                                 ConnectionEvent.UPDATE)
            self._emit(ConnectionEvent.UPDATE, state_change)
        else:
            self.notify_state(ConnectionState.CONNECTED, reason=reason)

        self.ably.channels._on_connected()

    def on_disconnected(self, msg: dict):
        error = msg.get("error")
        exception = AblyException.from_dict(error)
        self.notify_state(ConnectionState.DISCONNECTED, exception)
        if error:
            error_status_code = error.get("statusCode")
            if error_status_code >= 500 or error_status_code <= 504:  # RTN17f1
                if len(self.__fallback_hosts) > 0:
                    res = asyncio.create_task(self.connect_with_fallback_hosts(self.__fallback_hosts))
                    if not res:
                        return
                    self.notify_state(self.__fail_state, reason=res)
                else:
                    log.info("No fallback host to try for disconnected protocol message")

    async def on_error(self, msg: dict, exception: AblyException):
        if msg.get('channel') is None:  # RTN15i
            self.enact_state_change(ConnectionState.FAILED, exception)
            if self.transport:
                await self.transport.dispose()
            raise exception

    async def on_closed(self):
        if self.transport:
            await self.transport.dispose()
        if self.connect_base_task:
            self.connect_base_task.cancel()

    def on_channel_message(self, msg: dict):
        self.__ably.channels._on_channel_message(msg)

    def on_heartbeat(self, id: Optional[str]):
        if self.__ping_future:
            # Resolve on heartbeat from ping request.
            if self.__ping_id == id:
                if not self.__ping_future.cancelled():
                    self.__ping_future.set_result(None)
                self.__ping_future = None

    def deactivate_transport(self, reason=None):
        self.transport = None
        self.enact_state_change(ConnectionState.DISCONNECTED, reason)

    def request_state(self, state: ConnectionState, force=False):
        log.info(f'ConnectionManager.request_state(): state = {state}')

        if not force and state == self.state:
            return

        if state == ConnectionState.CONNECTING and self.__state == ConnectionState.CONNECTED:
            return

        if state == ConnectionState.CLOSING and self.__state == ConnectionState.CLOSED:
            return

        if not force:
            self.enact_state_change(state)

        if state == ConnectionState.CONNECTING:
            self.start_connect()

        if state == ConnectionState.CLOSING:
            asyncio.create_task(self.close_impl())

    def start_connect(self):
        self.start_suspend_timer()
        self.start_transition_timer(ConnectionState.CONNECTING)
        self.connect_base_task = asyncio.create_task(self.connect_base())

    async def connect_with_fallback_hosts(self, fallback_hosts: list):
        for host in fallback_hosts:
            try:
                if self.check_connection():
                    await self.try_host(host)
                    return
                else:
                    message = "Unable to connect, network unreachable"
                    log.exception(message)
                    exception = AblyException(message, status_code=404, code=80003)
                    self.notify_state(self.__fail_state, exception)
                    return
            except Exception as exc:
                exception = exc
                log.exception(f'Connection to {host} failed, reason={exception}')
        log.exception("No more fallback hosts to try")
        return exception

    async def connect_base(self):
        fallback_hosts = self.__fallback_hosts
        primary_host = self.options.get_realtime_host()
        try:
            await self.try_host(primary_host)
            return
        except Exception as exception:
            log.exception(f'Connection to {primary_host} failed, reason={exception}')
            if len(fallback_hosts) > 0:
                log.info("Attempting connection to fallback host(s)")
                resp = await self.connect_with_fallback_hosts(fallback_hosts)
                if not resp:
                    return
                exception = resp
            self.notify_state(self.__fail_state, reason=exception)

    async def try_host(self, host):
        params = self.__get_transport_params()
        self.transport = WebSocketTransport(self, host, params)
        self._emit('transport.pending', self.transport)
        self.transport.connect()

        future = asyncio.Future()

        def on_transport_connected():
            log.info('ConnectionManager.try_a_host(): transport connected')
            if self.transport:
                self.transport.off('failed', on_transport_failed)
            future.set_result(None)

        async def on_transport_failed(exception):
            log.info('ConnectionManager.try_a_host(): transport failed')
            if self.transport:
                self.transport.off('connected', on_transport_connected)
                await self.transport.dispose()
            future.set_exception(exception)

        self.transport.once('connected', on_transport_connected)
        self.transport.once('failed', on_transport_failed)
        #  Fix asyncio CancelledError in python 3.7
        try:
            await future
        except asyncio.CancelledError:
            return

    def notify_state(self, state: ConnectionState, reason=None, retry_immediately=None):
        # RTN15a
        retry_immediately = (retry_immediately is not False) and (
            state == ConnectionState.DISCONNECTED and self.__state == ConnectionState.CONNECTED)

        log.info(
            f'ConnectionManager.notify_state(): new state: {state}'
            + ('; will retry immediately' if retry_immediately else '')
        )

        if state == self.__state:
            return

        self.cancel_transition_timer()
        self.check_suspend_timer(state)

        if retry_immediately:
            self.options.loop.call_soon(self.request_state, ConnectionState.CONNECTING)
        elif state == ConnectionState.DISCONNECTED:
            self.start_retry_timer(self.options.disconnected_retry_timeout)
        elif state == ConnectionState.SUSPENDED:
            self.start_retry_timer(self.options.suspended_retry_timeout)

        if (state == ConnectionState.DISCONNECTED and not retry_immediately) or state == ConnectionState.SUSPENDED:
            self.disconnect_transport()

        self.enact_state_change(state, reason)

        if state == ConnectionState.CONNECTED:
            self.send_queued_messages()
        elif state in (
            ConnectionState.CLOSING,
            ConnectionState.CLOSED,
            ConnectionState.SUSPENDED,
            ConnectionState.FAILED,
        ):
            self.fail_queued_messages(reason)
            self.ably.channels._propagate_connection_interruption(state, reason)

    def start_transition_timer(self, state: ConnectionState, fail_state=None):
        log.debug(f'ConnectionManager.start_transition_timer(): transition state = {state}')

        if self.transition_timer:
            log.debug('ConnectionManager.start_transition_timer(): clearing already-running timer')
            self.transition_timer.cancel()

        if fail_state is None:
            fail_state = self.__fail_state if state != ConnectionState.CLOSING else ConnectionState.CLOSED

        timeout = self.options.realtime_request_timeout

        def on_transition_timer_expire():
            if self.transition_timer:
                self.transition_timer = None
                log.info(f'ConnectionManager {state} timer expired, notifying new state: {fail_state}')
                self.notify_state(
                    fail_state,
                    AblyException("Connection cancelled due to request timeout", 504, 50003)
                )

        log.debug(f'ConnectionManager.start_transition_timer(): setting timer for {timeout}ms')

        self.transition_timer = Timer(timeout, on_transition_timer_expire)

    def cancel_transition_timer(self):
        log.debug('ConnectionManager.cancel_transition_timer()')
        if self.transition_timer:
            self.transition_timer.cancel()
            self.transition_timer = None

    def start_suspend_timer(self):
        log.debug('ConnectionManager.start_suspend_timer()')
        if self.suspend_timer:
            return

        def on_suspend_timer_expire():
            if self.suspend_timer:
                self.suspend_timer = None
                log.info('ConnectionManager suspend timer expired, requesting new state: suspended')
                self.notify_state(
                    ConnectionState.SUSPENDED,
                    AblyException("Connection to server unavailable", 400, 80002)
                )
                self.__fail_state = ConnectionState.SUSPENDED
                self.__connection_details = None

        self.suspend_timer = Timer(Defaults.connection_state_ttl, on_suspend_timer_expire)

    def check_suspend_timer(self, state: ConnectionState):
        if state not in (
            ConnectionState.CONNECTING,
            ConnectionState.DISCONNECTED,
            ConnectionState.SUSPENDED,
        ):
            self.cancel_suspend_timer()

    def cancel_suspend_timer(self):
        log.debug('ConnectionManager.cancel_suspend_timer()')
        self.__fail_state = ConnectionState.DISCONNECTED
        if self.suspend_timer:
            self.suspend_timer.cancel()
            self.suspend_timer = None

    def start_retry_timer(self, interval: int):
        def on_retry_timeout():
            log.info('ConnectionManager retry timer expired, retrying')
            self.retry_timer = None
            self.request_state(ConnectionState.CONNECTING)

        self.retry_timer = Timer(interval, on_retry_timeout)

    def cancel_retry_timer(self):
        if self.retry_timer:
            self.retry_timer.cancel()
            self.retry_timer = None

    def disconnect_transport(self):
        log.info('ConnectionManager.disconnect_transport()')
        if self.transport:
            self.disconnect_transport_task = asyncio.create_task(self.transport.dispose())

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self):
        return self.__state

    @property
    def connection_details(self):
        return self.__connection_details
