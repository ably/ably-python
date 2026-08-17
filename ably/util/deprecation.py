"""Deprecation of the client constructors in favour of the pubsub package factories.

The `ably-pubsub-server` and `ably-pubsub-device` packages call the same
constructors internally, so they suppress the warning for the duration of the
call: the caller used the recommended entry point and has nothing to migrate.
"""

import warnings
from contextlib import contextmanager
from contextvars import ContextVar

# Set for the duration of a factory call in an Ably-authored pubsub package.
_suppressed: ContextVar = ContextVar('ably_constructor_deprecation_suppressed', default=False)


@contextmanager
def suppress_constructor_deprecation():
    """Silence the constructor deprecation warning within this block.

    This interface is only to be used by Ably-authored SDKs.
    """
    token = _suppressed.set(True)
    try:
        yield
    finally:
        _suppressed.reset(token)


def warn_constructor_deprecated(cls, factory: str, package: str) -> None:
    """Warn that constructing `cls` directly is deprecated.

    `factory` names the replacement entry point and `package` the distribution
    it lives in, so that the warning tells the reader exactly what to migrate to.
    """
    if _suppressed.get():
        return
    warnings.warn(
        f'{cls.__name__} is deprecated. Use {factory} from the {package} package instead, which '
        f'names the side your application runs on. {cls.__name__} keeps working and is not '
        f'scheduled for removal.',
        DeprecationWarning,
        # 1: this function, 2: the constructor, 3: the caller we want to point at.
        stacklevel=3,
    )
