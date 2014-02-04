import logging

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

        def handle(self, record):
            pass

        def createLock(self):
            return None

logger = logging.getLogger(__name__)
logger.addHandler(NullHandler())

from ably.rest.rest import AblyRest
from ably.rest.auth import Auth
from ably.types.channeloptions import ChannelOptions
from ably.types.options import Options
from ably.util.crypto import CipherParams
from ably.util.exceptions import AblyException
