import functools
from asyncio import events

from ably.executer.eventloop import AppEventLoop


def force_sync(fn):
    '''
    Forces async function to be used as sync function.
    Blocks execution of caller till result is returned.
    This decorator should only be used on async methods/coroutines.
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        app_loop: events = AppEventLoop.get_global().loop

        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            # Handle calls from app eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == app_loop:
                return res

            # Block the caller till result is returned
            future = asyncio.run_coroutine_threadsafe(res, app_loop)
            return future.result()
        return res

    return wrapper


def optional_sync(fn):
    '''
    Executes async function as a sync function if sync_enabled property on the given instance is true.
    This decorator should only be used on async methods/coroutines.
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'sync_enabled'):
            raise Exception("sync_enabled property should exist on instance to enable this feature")

        # Return awaitable as is!
        if not self.sync_enabled:
            return fn(self, *args, **kwargs)

        # Handle result of the given async method, with blocking behaviour
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        app_loop: events = self.app_loop.loop

        res = fn(self, *args, **kwargs)
        if asyncio.iscoroutine(res):
            # Handle calls from app eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == app_loop:
                return res

            # Block the caller till result is returned
            future = asyncio.run_coroutine_threadsafe(res, app_loop)
            return future.result()
        return res

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
    import asyncio

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        app_loop: events = self.app_loop.loop

        res = fn(self, *args, **kwargs)
        if asyncio.iscoroutine(res):
            # Handle calls from app eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == app_loop:
                return res

            # Handle calls from external eventloop, post them on app eventloop
            # Return awaitable back to external_eventloop
            future = asyncio.run_coroutine_threadsafe(res, app_loop)
            return asyncio.wrap_future(future)

        return res

    return wrapper


def close_app_eventloop(fn):
    import asyncio

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        # todo - this decorator will change if eventloop is also active for async operations
        if not self.sync_enabled:
            return fn(self, *args, **kwargs)

        app_loop: events = self.app_loop
        future = asyncio.run_coroutine_threadsafe(fn(self, *args, **kwargs), app_loop.loop)
        result = future.result()
        app_loop.close()
        return result

    return wrapper
