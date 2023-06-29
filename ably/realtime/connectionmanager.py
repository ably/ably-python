from __future__ import annotations
import logging
import asyncio
import httpx
from ably.transport.websockettransport import WebSocketTransport, ProtocolMessageAction
from ably.transport.defaults import Defaults
from ably.types.connectionerrors import ConnectionErrors
from ably.types.connectionstate import ConnectionEvent, ConnectionState, ConnectionStateChange
from ably.types.tokendetails import TokenDetails
from ably.util.exceptions import AblyException, IncompatibleClientIdException
from ably.util.eventemitter import EventEmitter
from datetime import datetime
from ably.util.helper import get_random_id, Timer, is_token_error
from typing import Optional, TYPE_CHECKING
from ably.types.connectiondetails import ConnectionDetails
from queue import Queue

if TYPE_CHECKING:
    from ably.realtime.realtime import AblyRealtime

log = logging.getLogger(__name__)


class ConnectionManager(EventEmitter):
    def __init__(self, realtime: AblyRealtime, initial_state):
        self.options = realtime.options
        self.__ably = realtime
        self.__state: ConnectionState = initial_state
        self.__ping_future: Optional[asyncio.Future] = None
        self.__timeout_in_secs: float = self.options.realtime_request_timeout / 1000
        self.transport: Optional[WebSocketTransport] = None
        self.__connection_details: Optional[ConnectionDetails] = None
        self.connection_id: Optional[str] = None
        self.__fail_state = ConnectionState.DISCONNECTED
        self.transition_timer: Optional[Timer] = None
        self.suspend_timer: Optional[Timer] = None
        self.retry_timer: Optional[Timer] = None
        self.connect_base_task: Optional[asyncio.Task] = None
        self.disconnect_transport_task: Optional[asyncio.Task] = None
        self.__fallback_hosts: list[str] = self.options.get_fallback_realtime_hosts()
        self.queued_messages: Queue = Queue()
        self.__error_reason: Optional[AblyException] = None
        super().__init__()

    def enact_state_change(self, state: ConnectionState, reason: Optional[AblyException] = None) -> None:
        current_state = self.__state
        log.debug(f'ConnectionManager.enact_state_change(): {current_state} -> {state}; reason = {reason}')
        self.__state = state
        if reason:
            self.__error_reason = reason
        self._emit('connectionstate', ConnectionStateChange(current_state, state, state, reason))

    def check_connection(self) -> bool:
        try:
            response = httpx.get(self.options.connectivity_check_url)
            return 200 <= response.status_code < 300 and \
                (self.options.connectivity_check_url != Defaults.connectivity_check_url or "yes" in response.text)
        except httpx.HTTPError:
            return False

    def get_state_error(self) -> AblyException:
        return ConnectionErrors[self.state]

    async def __get_transport_params(self) -> dict:
        protocol_version = Defaults.protocol_version
        params = await self.ably.auth.get_auth_transport_param()
        params["v"] = protocol_version
        if self.connection_details:
            params["resume"] = self.connection_details.connection_key
        return params

    async def close_impl(self) -> None:
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

    async def send_protocol_message(self, protocol_message: dict) -> None:
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

    def send_queued_messages(self) -> None:
        log.info(f'ConnectionManager.send_queued_messages(): sending {self.queued_messages.qsize()} message(s)')
        while not self.queued_messages.empty():
            asyncio.create_task(self.send_protocol_message(self.queued_messages.get()))

    def fail_queued_messages(self, err) -> None:
        log.info(
            f"ConnectionManager.fail_queued_messages(): discarding {self.queued_messages.qsize()} messages;" +
            f" reason = {err}"
        )
        while not self.queued_messages.empty():
            msg = self.queued_messages.get()
            log.exception(f"ConnectionManager.fail_queued_messages(): Failed to send protocol message: {msg}")

    async def ping(self) -> float:
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

    def on_connected(self, connection_details: ConnectionDetails, connection_id: str,
                     reason: Optional[AblyException] = None) -> None:
        self.__fail_state = ConnectionState.DISCONNECTED

        self.__connection_details = connection_details
        self.connection_id = connection_id

        if connection_details.client_id:
            try:
                self.ably.auth._configure_client_id(connection_details.client_id)
            except IncompatibleClientIdException as e:
                self.notify_state(ConnectionState.FAILED, reason=e)
                return

        if self.__state == ConnectionState.CONNECTED:
            state_change = ConnectionStateChange(ConnectionState.CONNECTED, ConnectionState.CONNECTED,
                                                 ConnectionEvent.UPDATE)
            self._emit(ConnectionEvent.UPDATE, state_change)
        else:
            self.notify_state(ConnectionState.CONNECTED, reason=reason)

        self.ably.channels._on_connected()

    async def on_disconnected(self, exception: AblyException) -> None:
        # RTN15h
        if self.transport:
            await self.transport.dispose()
        if exception:
            status_code = exception.status_code
            if status_code >= 500 and status_code <= 504:  # RTN17f1
                if len(self.__fallback_hosts) > 0:
                    try:
                        await self.connect_with_fallback_hosts(self.__fallback_hosts)
                    except Exception as e:
                        self.notify_state(self.__fail_state, reason=e)
                    return
                else:
                    log.info("No fallback host to try for disconnected protocol message")
            elif is_token_error(exception):
                await self.on_token_error(exception)
            else:
                self.notify_state(ConnectionState.DISCONNECTED, exception)
        else:
            log.warn("DISCONNECTED message received without error")

    async def on_token_error(self, exception: AblyException) -> None:
        if self.__error_reason is None or not is_token_error(self.__error_reason):
            self.__error_reason = exception
            try:
                await self.ably.auth._ensure_valid_auth_credentials(force=True)
            except Exception as e:
                self.on_error_from_authorize(e)
                return
            self.notify_state(self.__fail_state, exception, retry_immediately=True)
            return
        self.notify_state(self.__fail_state, exception)

    async def on_error(self, msg: dict, exception: AblyException) -> None:
        if msg.get("channel") is not None:  # RTN15i
            self.on_channel_message(msg)
            return
        if self.transport:
            await self.transport.dispose()
        if is_token_error(exception):  # RTN14b
            await self.on_token_error(exception)
        else:
            self.enact_state_change(ConnectionState.FAILED, exception)

    def on_error_from_authorize(self, exception: AblyException) -> None:
        log.info("ConnectionManager.on_error_from_authorize(): err = %s", exception)
        # RSA4a
        if exception.code == 40171:
            self.notify_state(ConnectionState.FAILED, exception)
        elif exception.status_code == 403:
            msg = 'Client configured authentication provider returned 403; failing the connection'
            log.error(f'ConnectionManager.on_error_from_authorize(): {msg}')
            self.notify_state(ConnectionState.FAILED, AblyException(msg, 403, 80019))
        else:
            msg = 'Client configured authentication provider request failed'
            log.warning(f'ConnectionManager.on_error_from_authorize: {msg}')
            self.notify_state(self.__fail_state, AblyException(msg, 401, 80019))

    async def on_closed(self) -> None:
        if self.transport:
            await self.transport.dispose()
        if self.connect_base_task:
            self.connect_base_task.cancel()

    def on_channel_message(self, msg: dict) -> None:
        self.__ably.channels._on_channel_message(msg)

    def on_heartbeat(self, id: Optional[str]) -> None:
        if self.__ping_future:
            # Resolve on heartbeat from ping request.
            if self.__ping_id == id:
                if not self.__ping_future.cancelled():
                    self.__ping_future.set_result(None)
                self.__ping_future = None

    def deactivate_transport(self, reason: Optional[AblyException] = None):
        self.transport = None
        self.notify_state(ConnectionState.DISCONNECTED, reason)

    def request_state(self, state: ConnectionState, force=False) -> None:
        log.debug(f'ConnectionManager.request_state(): state = {state}')

        if not force and state == self.state:
            return

        if state == ConnectionState.CONNECTING and self.__state == ConnectionState.CONNECTED:
            return

        if state == ConnectionState.CLOSING and self.__state == ConnectionState.CLOSED:
            return

        if state == ConnectionState.CONNECTING and self.__state in (ConnectionState.CLOSED,
                                                                    ConnectionState.FAILED):
            self.ably.channels._initialize_channels()

        if not force:
            self.enact_state_change(state)

        if state == ConnectionState.CONNECTING:
            self.start_connect()

        if state == ConnectionState.CLOSING:
            asyncio.create_task(self.close_impl())

    def start_connect(self) -> None:
        self.start_suspend_timer()
        self.start_transition_timer(ConnectionState.CONNECTING)
        self.connect_base_task = asyncio.create_task(self.connect_base())

    async def connect_with_fallback_hosts(self, fallback_hosts: list) -> Optional[Exception]:
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

    async def connect_base(self) -> None:
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

    async def try_host(self, host) -> None:
        try:
            params = await self.__get_transport_params()
        except AblyException as e:
            self.on_error_from_authorize(e)
            return
        self.transport = WebSocketTransport(self, host, params)
        self._emit('transport.pending', self.transport)
        self.transport.connect()

        future = asyncio.Future()

        def on_transport_connected():
            log.debug('ConnectionManager.try_a_host(): transport connected')
            if self.transport:
                self.transport.off('failed', on_transport_failed)
            if not future.done():
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

    def notify_state(self, state: ConnectionState, reason: Optional[AblyException] = None,
                     retry_immediately: Optional[bool] = None) -> None:
        # RTN15a
        retry_immediately = (retry_immediately is not False) and (
            state == ConnectionState.DISCONNECTED and self.__state == ConnectionState.CONNECTED)

        log.debug(
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

    def start_transition_timer(self, state: ConnectionState, fail_state: Optional[ConnectionState] = None) -> None:
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

    def start_suspend_timer(self) -> None:
        log.debug('ConnectionManager.start_suspend_timer()')
        if self.suspend_timer:
            return

        def on_suspend_timer_expire() -> None:
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

    def check_suspend_timer(self, state: ConnectionState) -> None:
        if state not in (
            ConnectionState.CONNECTING,
            ConnectionState.DISCONNECTED,
            ConnectionState.SUSPENDED,
        ):
            self.cancel_suspend_timer()

    def cancel_suspend_timer(self) -> None:
        log.debug('ConnectionManager.cancel_suspend_timer()')
        self.__fail_state = ConnectionState.DISCONNECTED
        if self.suspend_timer:
            self.suspend_timer.cancel()
            self.suspend_timer = None

    def start_retry_timer(self, interval: int) -> None:
        def on_retry_timeout():
            log.info('ConnectionManager retry timer expired, retrying')
            self.retry_timer = None
            self.request_state(ConnectionState.CONNECTING)

        self.retry_timer = Timer(interval, on_retry_timeout)

    def cancel_retry_timer(self) -> None:
        if self.retry_timer:
            self.retry_timer.cancel()
            self.retry_timer = None

    def disconnect_transport(self) -> None:
        log.info('ConnectionManager.disconnect_transport()')
        if self.transport:
            self.disconnect_transport_task = asyncio.create_task(self.transport.dispose())

    async def on_auth_updated(self, token_details: TokenDetails):
        log.info(f"ConnectionManager.on_auth_updated(): state = {self.state}")
        if self.state == ConnectionState.CONNECTED:
            auth_message = {
                "action": ProtocolMessageAction.AUTH,
                "auth": {
                    "accessToken": token_details.token
                }
            }
            await self.send_protocol_message(auth_message)

            state_change = await self.once_async()

            if state_change.current == ConnectionState.CONNECTED:
                return
            elif state_change.current == ConnectionState.FAILED:
                raise state_change.reason
        elif self.state == ConnectionState.CONNECTING:
            if self.connect_base_task and not self.connect_base_task.done():
                self.connect_base_task.cancel()
            if self.transport:
                await self.transport.dispose()
        if self.state != ConnectionState.CONNECTED:
            future = asyncio.Future()

            def on_state_change(state_change: ConnectionStateChange) -> None:
                if state_change.current == ConnectionState.CONNECTED:
                    self.off('connectionstate', on_state_change)
                    future.set_result(token_details)
                if state_change.current in (
                        ConnectionState.CLOSED,
                        ConnectionState.FAILED,
                        ConnectionState.SUSPENDED
                ):
                    self.off('connectionstate', on_state_change)
                    future.set_exception(state_change.reason or self.get_state_error())

            self.on('connectionstate', on_state_change)

            if self.state == ConnectionState.CONNECTING:
                self.start_connect()
            else:
                self.request_state(ConnectionState.CONNECTING)

            return await future

    @property
    def ably(self):
        return self.__ably

    @property
    def state(self) -> ConnectionState:
        return self.__state

    @property
    def connection_details(self) -> Optional[ConnectionDetails]:
        return self.__connection_details
