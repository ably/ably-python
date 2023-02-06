import logging
import asyncio
from ably.realtime.connection import Connection, ConnectionState
from ably.rest.auth import Auth
from ably.rest.rest import AblyRest
from ably.types.options import Options
from ably.rest.channel import Channels as RestChannels
from ably.realtime.realtime_channel import ChannelState, RealtimeChannel


log = logging.getLogger(__name__)


class AblyRealtime(AblyRest):
    """
    Ably Realtime Client

    Attributes
    ----------
    loop: AbstractEventLoop
        asyncio running event loop
    auth: Auth
        authentication object
    options: Options
        auth options object
    connection: Connection
        realtime connection object
    channels: Channels
        realtime channel object

    Methods
    -------
    connect()
        Establishes the realtime connection
    close()
        Closes the realtime connection
    """

    def __init__(self, key=None, loop=None, **kwargs):
        """Constructs a RealtimeClient object using an Ably API key.

        Parameters
        ----------
        key: str
            A valid ably API key string
        loop: AbstractEventLoop, optional
            asyncio running event loop
        auto_connect: bool
            When true, the client connects to Ably as soon as it is instantiated.
            You can set this to false and explicitly connect to Ably using the
            connect() method. The default is true.
        **kwargs: client options
            realtime_host: str
                Enables a non-default Ably host to be specified for realtime connections.
                For development environments only. The default value is realtime.ably.io.
            environment: str
                Enables a custom environment to be used with the Ably service. Defaults to `production`
            realtime_request_timeout: float
                Timeout (in milliseconds) for the wait of acknowledgement for operations performed via a realtime
                connection. Operations include establishing a connection with Ably, or sending a HEARTBEAT,
                CONNECT, ATTACH, DETACH or CLOSE request. The default is 10 seconds(10000 milliseconds).
            disconnected_retry_timeout: float
                If the connection is still in the DISCONNECTED state after this delay, the client library will
                attempt to reconnect automatically. The default is 15 seconds.
            channel_retry_timeout: float
                When a channel becomes SUSPENDED following a server initiated DETACHED, after this delay, if the
                channel is still SUSPENDED and the connection is in CONNECTED, the client library will attempt to
                re-attach the channel automatically. The default is 15 seconds.
            fallback_hosts: list[str]
                An array of fallback hosts to be used in the case of an error necessitating the use of an
                alternative host. If you have been provided a set of custom fallback hosts by Ably, please specify
                them here.
            connection_state_ttl: float
                The duration that Ably will persist the connection state for when a Realtime client is abruptly
                disconnected.
            suspended_retry_timeout: float
                When the connection enters the SUSPENDED state, after this delay, if the state is still SUSPENDED,
                the client library attempts to reconnect automatically. The default is 30 seconds.
            connectivity_check_url: string
                Override the URL used by the realtime client to check if the internet is available.
                In the event of a failure to connect to the primary endpoint, the client will send a
                GET request to this URL to check if the internet is available. If this request returns
                a success response the client will attempt to connect to a fallback host.
        Raises
        ------
        ValueError
            If no authentication key is not provided
        """
        # RTC1
        super().__init__(key, **kwargs)

        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                log.warning('Realtime client created outside event loop')

        if key is not None:
            options = Options(key=key, loop=loop, **kwargs)
        else:
            raise ValueError("Key is missing. Provide an API key.")

        log.info(f'Realtime client initialised with options: {vars(options)}')

        self.__auth = Auth(self, options)
        self.__options = options
        self.key = key
        self.__connection = Connection(self)
        self.__channels = Channels(self)

        # RTN3
        if options.auto_connect:
            self.connection.connection_manager.request_state(ConnectionState.CONNECTING, force=True)

    # RTC15
    def connect(self):
        """Establishes a realtime connection.

        Explicitly calling connect() is unnecessary unless the autoConnect attribute of the ClientOptions object
        is false. Unless already connected or connecting, this method causes the connection to open, entering the
        CONNECTING state.
        """
        log.info('Realtime.connect() called')
        # RTC15a
        self.connection.connect()

    # RTC16
    async def close(self):
        """Causes the connection to close, entering the closing state.
        Once closed, the library will not attempt to re-establish the
        connection without an explicit call to connect()
        """
        log.info('Realtime.close() called')
        # RTC16a
        await self.connection.close()
        await super().close()

    # RTC4
    @property
    def auth(self):
        """Returns the auth object"""
        return self.__auth

    @property
    def options(self):
        """Returns the auth options object"""
        return self.__options

    # RTC2
    @property
    def connection(self):
        """Returns the realtime connection object"""
        return self.__connection

    # RTC3, RTS1
    @property
    def channels(self):
        """Returns the realtime channel object"""
        return self.__channels


class Channels(RestChannels):
    """Creates and destroys RealtimeChannel objects.

    Methods
    -------
    get(name)
        Gets a channel
    release(name)
        Releases a channel
    """

    # RTS3
    def get(self, name) -> RealtimeChannel:
        """Creates a new RealtimeChannel object, or returns the existing channel object.

        Parameters
        ----------

        name: str
            Channel name
        """
        if name not in self.__all:
            channel = self.__all[name] = RealtimeChannel(self.__ably, name)
        else:
            channel = self.__all[name]
        return channel

    # RTS4
    def release(self, name):
        """Releases a RealtimeChannel object, deleting it, and enabling it to be garbage collected

        It also removes any listeners associated with the channel.
        To release a channel, the channel state must be INITIALIZED, DETACHED, or FAILED.


        Parameters
        ----------
        name: str
            Channel name
        """
        if name not in self.__all:
            return
        del self.__all[name]

    def _on_channel_message(self, msg):
        channel_name = msg.get('channel')
        if not channel_name:
            log.error(
                'Channels.on_channel_message()',
                f'received event without channel, action = {msg.get("action")}'
            )
            return

        channel = self.__all[channel_name]
        if not channel:
            log.warning(
                'Channels.on_channel_message()',
                f'receieved event for non-existent channel: {channel_name}'
            )
            return

        channel._on_message(msg)

    def _propagate_connection_interruption(self, state: ConnectionState, reason):
        from_channel_states = (
            ChannelState.ATTACHING,
            ChannelState.ATTACHED,
            ChannelState.DETACHING,
            ChannelState.SUSPENDED,
        )

        connection_to_channel_state = {
            ConnectionState.CLOSING: ChannelState.DETACHED,
            ConnectionState.CLOSED: ChannelState.DETACHED,
            ConnectionState.FAILED: ChannelState.FAILED,
            ConnectionState.SUSPENDED: ChannelState.SUSPENDED,
        }

        for channel_name in self.__all:
            channel = self.__all[channel_name]
            if channel.state in from_channel_states:
                channel._notify_state(connection_to_channel_state[state], reason)

    def _on_connected(self):
        for channel_name in self.__all:
            channel = self.__all[channel_name]
            if channel.state == ChannelState.ATTACHING or channel.state == ChannelState.DETACHING:
                channel._check_pending_state()
            elif channel.state == ChannelState.SUSPENDED:
                asyncio.create_task(channel.attach())
            elif channel.state == ChannelState.ATTACHED:
                channel._request_state(ChannelState.ATTACHING)
