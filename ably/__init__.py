import logging


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

requests_log = logging.getLogger('requests')
requests_log.setLevel(logging.WARNING)

from ably.rest.rest import AblyRest
from ably.rest.auth import Auth
from ably.rest.push import Push
from ably.types.capability import Capability
from ably.types.channelsubscription import PushChannelSubscription
from ably.types.device import DeviceDetails
from ably.types.options import Options
from ably.util.crypto import CipherParams
from ably.util.exceptions import AblyException, AblyAuthException, IncompatibleClientIdException

api_version = '1.1'
lib_version = '1.1.1'
