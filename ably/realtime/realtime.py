import logging
import asyncio
from ably.realtime.connection import Connection
from ably.rest.auth import Auth
from ably.types.options import Options
from ably.realtime.realtime_channel import RealtimeChannel


log = logging.getLogger(__name__)


class AblyRealtime:
    """
    Ably Realtime Client

    Attributes
    ----------
    key: str
        A valid ably key string
    loop: AbstractEventLoop
        asyncio running event loop
    auth: Auth
        authentication object
    options: Options
        auth options
    connection: Connection
        realtime connection object
    channels: Channels
        realtime channel object

    Methods
    -------
    connect()
        Establishes a realtime connection
    close()
        Closes a realtime connection
    ping()
        Pings a realtime connection
    """

    def __init__(self, key=None, loop=None, **kwargs):
        """Constructs a RealtimeClient object using an Ably API key or token string.

        Parameters
        ----------
        key: str
            A valid ably key string
        loop: AbstractEventLoop, optional
            asyncio running event loop

        Raises
        ------
        ValueError
            If no authentication key is not provided
        """
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                log.warning('Realtime client created outside event loop')

        if key is not None:
            options = Options(key=key, loop=loop, **kwargs)
        else:
            raise ValueError("Key is missing. Provide an API key.")

        self.__auth = Auth(self, options)
        self.__options = options
        self.key = key
        self.__connection = Connection(self)
        self.__channels = Channels(self)

        if options.auto_connect:
            asyncio.ensure_future(self.connection.connection_manager.connect_impl())

    async def connect(self):
        """Establishes a realtime connection.

        Explicitly calling connect() is unnecessary unless the autoConnect attribute of the ClientOptions object
        is false. Unless already connected or connecting, this method causes the connection to open, entering the
        CONNECTING state.
        """
        await self.connection.connect()

    async def close(self):
        """Causes the connection to close, entering the closing state.

        Once closed, the library will not attempt to re-establish the
        connection without an explicit call to connect()
        """
        await self.connection.close()

    async def ping(self):
        """Send a ping to the realtime connection

        When connected, sends a heartbeat ping to the Ably server and executes
        the callback with any error and the response time in milliseconds when
        a heartbeat ping request is echoed from the server.

        Returns
        -------
        float
            The response time in milliseconds
        """
        return await self.connection.ping()

    @property
    def auth(self):
        """Returns the auth object"""
        return self.__auth

    @property
    def options(self):
        """Returns the auth options object"""
        return self.__options

    @property
    def connection(self):
        """Returns the realtime connection object"""
        return self.__connection

    @property
    def channels(self):
        """Returns the realtime channel object"""
        return self.__channels


class Channels:
    """
    Establish ably realtime channel

    Attributes
    ----------
    realtime: any
        Ably realtime client object

    Methods
    -------
    get(name)
        Gets a channel
    release(name)
        Releases a channel
    on_channel_message(msg)
        Receives message on a channel
    """

    def __init__(self, realtime):
        """Initial a realtime channel using the realtime object

        Parameters
        ----------
        realtime: any
            Ably realtime client object
        """
        self.all = {}
        self.__realtime = realtime

    def get(self, name):
        """Creates a new RealtimeChannel object, or returns the existing channel object.

        Parameters
        ----------

        name: str
            Channel name
        """
        if not self.all.get(name):
            self.all[name] = RealtimeChannel(self.__realtime, name)
        return self.all[name]

    def release(self, name):
        """Releases a RealtimeChannel object, deleting it, and enabling it to be garbage collected

        It also removes any listeners associated with the channel.
        To release a channel, the channel state must be INITIALIZED, DETACHED, or FAILED.


        Parameters
        ----------
        name: str
            Channel name
        """
        if not self.all.get(name):
            return
        del self.all[name]

    def on_channel_message(self, msg):
        """Receives message on a realtime channel

        Parameters
        ----------
        msg: str
            Channel message to receive
        """
        channel = self.all.get(msg.get('channel'))
        if not channel:
            log.warning('Channel message received but no channel instance found')
        channel.on_message(msg)
