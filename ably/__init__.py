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
