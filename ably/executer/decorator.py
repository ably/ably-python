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
        app_loop: events = AppEventLoop.current().loop

        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            # Handle calls from app eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == app_loop:
                return app_loop.create_task(res)

            # Block the caller till result is returned
            future = asyncio.run_coroutine_threadsafe(res, app_loop)
            return future.result()
        return res

    return wrapper


def optional_sync(fn):
    '''
    Executes async function as a sync function if sync_enabled property on the given instance is true.
    Blocks execution of caller till result is returned.
    This decorator should only be used on async methods/coroutines.
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'sync_enabled'):
            raise Exception("sync_enabled property should exist on instance to enable this feature")

        # Return awaitable like a normal async method if sync is not enabled
        if not self.sync_enabled:
            return asyncio.create_task(fn(self, *args, **kwargs))

        # Handle result of the given async method, with blocking behaviour
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        app_loop: events = AppEventLoop.current().loop

        res = fn(self, *args, **kwargs)
        if asyncio.iscoroutine(res):
            # Handle calls from app eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == app_loop:
                return app_loop.create_task(res)

            # Block the caller till result is returned
            future = asyncio.run_coroutine_threadsafe(res, app_loop)
            return future.result()
        return res

    return wrapper


def close_app_eventloop(fn):
    import asyncio

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):

        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass

        app_eventloop: events = AppEventLoop.current()
        if caller_eventloop is not None:
            app_eventloop.close()
            return caller_eventloop.create_task(fn(*args, **kwargs))
        else:
            future = asyncio.run_coroutine_threadsafe(fn(*args, **kwargs), app_eventloop.loop)
            result = future.result()
            app_eventloop.close()
            return result

    return wrapper
