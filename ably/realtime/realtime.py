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

        log.info(f'Realtime client initialised with options: {vars(options)}')

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
        log.info('Realtime.connect() called')
        await self.connection.connect()

    async def close(self):
        """Causes the connection to close, entering the closing state.
        Once closed, the library will not attempt to re-establish the
        connection without an explicit call to connect()
        """
        log.info('Realtime.close() called')
        await self.connection.close()

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
    """Creates and destroys RealtimeChannel objects.

    Methods
    -------
    get(name)
        Gets a channel
    release(name)
        Releases a channel
    """

    def __init__(self, realtime):
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

    def _on_channel_message(self, msg):
        channel_name = msg.get('channel')
        if not channel_name:
            log.error(
                'Channels.on_channel_message()',
                f'received event without channel, action = {msg.get("action")}'
            )
            return

        channel = self.all.get(msg.get('channel'))
        if not channel:
            log.warning(
                'Channels.on_channel_message()',
                f'receieved event for non-existent channel: {channel_name}'
            )
            return

        channel._on_message(msg)
