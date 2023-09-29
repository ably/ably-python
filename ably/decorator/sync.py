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


def enable_optional_sync(fn):
    '''
    turn an async function to sync function
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        existing_loop = None
        try:
            existing_loop = asyncio.get_running_loop()
        except:
            pass
        loop = get_custom_event_loop()
        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            future = asyncio.run_coroutine_threadsafe(res, loop)
            if existing_loop is not None and existing_loop.is_running():
                return asyncio.wrap_future(future)
            return future.result()
        return res

    return wrapper
