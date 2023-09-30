import functools
from asyncio import events

from ably.executer.eventloop import AppEventLoop


def run_safe(fn):
    '''
    USAGE :
    If called from an eventloop or coroutine, returns a future, doesn't block external eventloop.
    If called from a regular function, returns a blocking result.
    Also makes async/sync workflow thread safe.
    This decorator should only be used on async methods/coroutines.
    Completely safe to use for existing async users.
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        ably_eventloop: events = AppEventLoop.current().loop

        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            # Handle calls from ably_eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == ably_eventloop:
                return ably_eventloop.create_task(res)

            future = asyncio.run_coroutine_threadsafe(res, ably_eventloop)

            # Handle calls from external eventloop, post them on ably_eventloop
            # Return future back to external_eventloop
            if caller_eventloop is not None and caller_eventloop.is_running():
                return asyncio.wrap_future(future)

            # If called from regular function, return blocking result
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
