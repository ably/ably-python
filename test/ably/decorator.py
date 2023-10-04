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
