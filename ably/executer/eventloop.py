import asyncio
import threading
from asyncio import events


class AppEventLoop:
    _global: 'AppEventLoop' = None

    __loop: events
    __thread: threading
    __is_active: bool

    def __init__(self, loop=None, thread=None):
        if not loop.is_running:
            raise Exception("Provided eventloop must be in running state")
        self.__loop = loop
        self.__thread = thread
        self.__is_active = True

    @staticmethod
    def get_global() -> 'AppEventLoop':
        if AppEventLoop._global is None or not AppEventLoop._global.__is_active:
            AppEventLoop._global = AppEventLoop.create(True)
        return AppEventLoop._global

    @staticmethod
    def create(background=False) -> 'AppEventLoop':
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, daemon=background)
        thread.start()
        return AppEventLoop(loop, thread)

    @property
    def loop(self):
        return self.__loop

    def run(self, coro, callback):
        self.__loop.call_soon()

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

        future = asyncio.run_coroutine_threadsafe(coro, self.__loop)
        return future.result()

    def run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.__loop)
        return asyncio.wrap_future(future)

    def close(self) -> events:
        if self.__thread is not None:
            if self.__loop is not None and self.__loop.is_running():
                self.__loop.call_soon_threadsafe(self.__loop.stop)
            self.__thread.join()
        self.__is_active = False
