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

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)

from ably.rest.rest import AblyRest
from ably.rest.auth import Auth
from ably.types.capability import Capability
from ably.types.options import Options
from ably.util.crypto import CipherParams
from ably.util.exceptions import AblyException, AblyAuthException, IncompatibleClientIdException

api_version = '1.0'
lib_version = '1.0.0'
