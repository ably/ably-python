import asyncio
import functools
import threading
from asyncio import events

_loop: events = None
_thread: threading = None


def get_custom_event_loop() -> events:
    global _loop, _thread
    if _thread is None:
        if _loop is None:
            _loop = asyncio.new_event_loop()
        if not _loop.is_running():
            _thread = threading.Thread(
                target=_loop.run_forever,
                daemon=True)
            _thread.start()
    return _loop


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
        ably_eventloop: events = get_custom_event_loop()

        # Handle calls from ably_eventloop on the same loop, return awaitable
        if caller_eventloop is not None and caller_eventloop == ably_eventloop:
            return ably_eventloop.create_task(fn(*args, **kwargs))

        # Post external calls on ably_eventloop, return awaitable on calling eventloop
        future = asyncio.run_coroutine_threadsafe(fn(*args, **kwargs), ably_eventloop)
        if caller_eventloop is not None and caller_eventloop.is_running():
            return asyncio.wrap_future(future)

        # If called from regular function instead of coroutine, block till result is available
        return future.result()

    return wrapper
