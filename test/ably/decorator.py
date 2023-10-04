import functools
from asyncio import events

from ably.executer.eventloop import AppEventLoop


def force_sync(fn):
    '''
    Forces async function to be used as sync function.
    Blocks execution of caller till result is returned.
    This decorator should only be used on async methods/coroutines.
    '''

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        app_loop: events = AppEventLoop.get_global()
        return app_loop.run_sync(fn(*args, **kwargs))

    return wrapper
