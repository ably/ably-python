import asyncio
from asyncio import events


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
        # Handle result of the given async method, with blocking behaviour
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass

        if asyncio.iscoroutine(coro):
            # Handle calls from app eventloop on the same loop, return awaitable
            # Can't wait on calling thread/eventloop, it will be blocked,
            # In blocking state, it can't execute coroutine at the same time.
            if caller_eventloop is not None and caller_eventloop == loop:
                return coro

            # Block the caller till result is returned
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return coro

    @staticmethod
    def run_safe_async(loop: events, coro):
        caller_eventloop = None
        try:
            caller_eventloop: events = asyncio.get_running_loop()
        except Exception:
            pass

        if asyncio.iscoroutine(coro):
            # Handle calls from app eventloop on the same loop, return awaitable
            if caller_eventloop is not None and caller_eventloop == loop:
                return coro

            # Handle calls from external eventloop, post them on app eventloop
            # Return awaitable back to external_eventloop
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return asyncio.wrap_future(future, loop=caller_eventloop)

        return coro

    # async def force_regular_fn_async(loop: events, regular_fn, regular_fn_args):
    #     # Run in the default loop's executor
    #     return await loop.run_in_executor(None, blocking_fn, blocking_fn_args)

    @staticmethod
    # Run blocking function in default threadpool executor.
    async def run_blocking_fn_async(loop: events, blocking_fn, blocking_fn_args):
        # Run in the default loop's executor
        return await loop.run_in_executor(None, blocking_fn, blocking_fn_args)
