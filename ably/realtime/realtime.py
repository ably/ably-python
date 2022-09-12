import logging
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
            options = Options(**kwargs)

        self.__auth = Auth(self, options)

        self.__options = options
    
    @property
    def auth(self):
        return self.__auth

    @property
    def options(self):
        return self.__options
