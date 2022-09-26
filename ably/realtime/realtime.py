import logging
from ably.realtime.connection import Connection
from ably.rest.auth import Auth
from ably.types.options import Options


log = logging.getLogger(__name__)


class AblyRealtime:
    """Ably Realtime Client"""

    def __init__(self, key=None, **kwargs):
        """Create an AblyRealtime instance.

        :Parameters:
          **Credentials**
          - `key`: a valid ably key string
        """

        if key is not None:
            options = Options(key=key, **kwargs)
        else:
            raise ValueError("Key is missing. Provide an API key.")

        self.__auth = Auth(self, options)
        self.__options = options
        self.key = key
        self.__connection = Connection(self)

    async def connect(self):
        await self.connection.connect()

    async def close(self):
        await self.connection.close()

    @property
    def auth(self):
        return self.__auth

    @property
    def options(self):
        return self.__options

    @property
    def connection(self):
        """Establish realtime connection"""
        return self.__connection
