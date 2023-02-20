import inspect
import random
import string
import asyncio
import time
from typing import Callable


def get_random_id():
    # get random string of letters and digits
    source = string.ascii_letters + string.digits
    random_id = ''.join((random.choice(source) for i in range(8)))
    return random_id


def is_callable_or_coroutine(value):
    return asyncio.iscoroutinefunction(value) or inspect.isfunction(value) or inspect.ismethod(value)


def unix_time_ms():
    return round(time.time_ns() / 1_000_000)


def is_token_error(exception):
    return 40140 <= exception.code < 40150


class Timer:
    def __init__(self, timeout: float, callback: Callable):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout / 1000)
        if asyncio.iscoroutinefunction(self._callback):
            await self._callback()
        else:
            self._callback()

    def cancel(self):
        self._task.cancel()
