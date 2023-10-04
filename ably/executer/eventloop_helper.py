import asyncio
from asyncio import events
from concurrent.futures import Future


class LoopHelper:
    @staticmethod
    def run(loop: events, coro, callback):
        raise "not implemented"

    @staticmethod
    def run_safe(loop: events, coro, callback):
        raise "not implemented"

    #
    @staticmethod
    def force_sync(loop: events, coro):
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

    @staticmethod
    def run_safe_async(loop: events, coro):
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

    @staticmethod
    # Run blocking function in default threadpool executor.
    async def run_blocking_fn_async(loop: events, blocking_fn, blocking_fn_args):
        # Run in the default loop's executor
        return await loop.run_in_executor(None, blocking_fn, blocking_fn_args)
