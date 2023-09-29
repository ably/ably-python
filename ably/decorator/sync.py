import asyncio
import functools
import threading

_loop = None
_thread = None


def get_custom_event_loop():
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
            caller_eventloop = asyncio.get_running_loop()
        except:
            pass
        ably_eventloop = get_custom_event_loop()
        future = asyncio.run_coroutine_threadsafe(fn(*args, **kwargs), ably_eventloop)
        if caller_eventloop is not None and caller_eventloop.is_running():
            return asyncio.wrap_future(future)
        return future.result()

    return wrapper
