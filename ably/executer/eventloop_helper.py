import asyncio
from asyncio import events
from concurrent.futures import Future


class LoopHelper:
    @classmethod
    def run(cls, loop: events, coro, callback):
        raise "not implemented"

    @classmethod
    def run_safe(cls, loop: events, coro, callback):
        raise "not implemented"

    #
    @classmethod
    def force_sync(cls, loop: events, coro):
        future: Future
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        # Handle calls from app eventloop on the same loop, return awaitable
        if caller_eventloop is not None and caller_eventloop == loop:
            raise "can't wait/force sync on the same loop, eventloop will be blocked"

        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    @classmethod
    def run_safe_async(cls, loop: events, coro):
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass
        if caller_eventloop is not None and caller_eventloop == loop:
            return coro

        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return asyncio.wrap_future(future, loop=caller_eventloop)

    # async def force_regular_fn_async(loop: events, regular_fn, regular_fn_args):
    #     # Run in the default loop's executor
    #     return await loop.run_in_executor(None, blocking_fn, blocking_fn_args)

    @classmethod
    # Run blocking function in default threadpool executor.
    async def run_blocking_fn_async(cls, loop: events, blocking_fn, blocking_fn_args):
        # Run in the default loop's executor
        return await loop.run_in_executor(None, blocking_fn, blocking_fn_args)
