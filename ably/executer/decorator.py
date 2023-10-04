import functools
from asyncio import events


def optional_sync(fn):
    '''
    Executes async function as a sync function if sync_enabled property on the given instance is true.
    This decorator should only be used on async methods/coroutines.
    '''

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        # Return awaitable as is!
        if not self.sync_enabled:
            return fn(self, *args, **kwargs)

        return self.app_loop.run_sync(fn(self, *args, **kwargs))

    return wrapper


def run_safe_async(fn):
    '''
    USAGE :
    Executes given async function/coroutine on the internal eventloop.
    This is to make sure external thread/eventloop doesn't block/disrupt internal workflow.
    This will be mainly needed on realtime-client public methods.
    More information - https://github.com/ably/ably-python/issues/534
    This decorator should only be used on async methods/coroutines.
    '''

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        return self.app_loop.run_async(fn(self, *args, **kwargs))

    return wrapper


def close_app_eventloop(fn):

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        # todo - this decorator will change if eventloop is also active for async operations
        if not self.sync_enabled:
            return fn(self, *args, **kwargs)

        app_loop: events = self.app_loop
        result = app_loop.run_sync(fn(self, *args, **kwargs))
        app_loop.close()
        return result

    return wrapper
