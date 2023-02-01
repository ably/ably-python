import functools
import logging
from ably.realtime.connectionmanager import ConnectionManager
from ably.types.connectionstate import ConnectionEvent, ConnectionState
from ably.util.eventemitter import EventEmitter

log = logging.getLogger(__name__)


class Connection(EventEmitter):  # RTN4
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
        self.__connection_manager.on('connectionstate', self._on_state_update)  # RTN4a
        self.__connection_manager.on('update', self._on_connection_update)  # RTN4h
        super().__init__()

    # RTN11
    def connect(self):
        """Establishes a realtime connection.

        Causes the connection to open, entering the connecting state
        """
        self.__error_reason = None
        self.connection_manager.request_state(ConnectionState.CONNECTING)

    async def close(self):
        """Causes the connection to close, entering the closing state.

        Once closed, the library will not attempt to re-establish the
        connection without an explicit call to connect()
        """
        self.connection_manager.request_state(ConnectionState.CLOSING)
        await self.once_async(ConnectionState.CLOSED)

    # RTN13
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

    def _on_connection_update(self, state_change):
        self.__realtime.options.loop.call_soon(functools.partial(self._emit, ConnectionEvent.UPDATE, state_change))

    # RTN4d
    @property
    def state(self):
        """The current connection state of the connection"""
        return self.__state

    # RTN25
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

    @property
    def connection_details(self):
        return self.__connection_manager.connection_details
