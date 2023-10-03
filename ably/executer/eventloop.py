import asyncio
import threading
from asyncio import events


class AppEventLoop:
    _global: 'AppEventLoop' = None

    loop: events
    thread: threading
    is_active: bool

    def __init__(self):
        self.loop = None
        self.thread = None
        self.is_active = False

    @staticmethod
    def get_global() -> 'AppEventLoop':
        if AppEventLoop._global is None or not AppEventLoop._global.is_active:
            AppEventLoop._global = AppEventLoop.create(True)
        return AppEventLoop._global

    @staticmethod
    def create(background=False) -> 'AppEventLoop':
        app_loop = AppEventLoop()
        app_loop.loop = asyncio.new_event_loop()
        app_loop.thread = threading.Thread(target=app_loop.loop.run_forever, daemon=background)
        app_loop.thread.start()
        app_loop.is_active = True
        return app_loop

    def run(self, coro, callback):
        self.loop.call_soon()

    def run_sync(self, coro):
        # todo - can only handle run_sync from different thread than app_loop
        # caller_eventloop = None
        # try:
        #     caller_eventloop: events = asyncio.get_running_loop()
        # except Exception:
        #     pass
        # Handle calls from app eventloop on the same loop, return awaitable
        # if caller_eventloop is not None and caller_eventloop == self.loop:
        #     task = self.loop.create_task(coro)
        #     task.add_done_callback

        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return asyncio.wrap_future(future)

    def _close(self):
        if self.loop is not None and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread is not None:
            self.thread.join()
        self.is_active = False

    def close(self) -> events:
        if self == AppEventLoop._global:  # Global eventloop is shared amongst multiple client instances.
            return                        # It will be reused, and closed automatically once process ends.
        self._close()
