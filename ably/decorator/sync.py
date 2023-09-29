import functools
from asyncio import events

from ably.executer.eventloop import AblyEventLoop


def optional_sync(fn):
    '''
    Enables async function to be used as both sync and async function.
    Also makes async/sync workflow thread safe.
    This decorator should only be used on async methods/coroutines.
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except:
            pass
        ably_eventloop: events = AblyEventLoop.get_global().loop

        # Handle calls from ably_eventloop on the same loop, return awaitable
        if caller_eventloop is not None and caller_eventloop == ably_eventloop:
            return ably_eventloop.create_task(fn(*args, **kwargs))

        # Post external calls on ably_eventloop, return awaitable on calling eventloop
        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            future = asyncio.run_coroutine_threadsafe(res, ably_eventloop)
            if caller_eventloop is not None and caller_eventloop.is_running():
                return asyncio.wrap_future(future)
            return future.result()
        return res

    return wrapper
