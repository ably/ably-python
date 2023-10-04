import asyncio
import threading
from asyncio import events

from ably.executer.eventloop_helper import LoopHelper


class AppEventLoop:
    _global: 'AppEventLoop' = None

    __loop: events
    __thread: threading
    __is_active: bool

    def __init__(self, loop, thread=None):
        if not loop.is_running:
            raise Exception("Provided eventloop must be in running state")
        self.__loop = loop
        self.__thread = thread
        self.__is_active = True

    @classmethod
    def get_global(cls) -> 'AppEventLoop':
        if cls._global is None or not cls._global.__is_active:
            cls._global = cls.create()
        return cls._global

    @classmethod
    def create(cls, background=True) -> 'AppEventLoop':
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, daemon=background)
        thread.start()
        return cls(loop, thread)

    @property
    def loop(self):
        return self.__loop

    def run_sync(self, coro):
        return LoopHelper.run_safe_sync(self.loop, coro)

    def run_async(self, coro):
        return LoopHelper.run_safe_async(self.loop, coro)

    def close(self) -> events:
        if self.__thread is not None:
            if self.__loop is not None and self.__loop.is_running():
                self.__loop.call_soon_threadsafe(self.__loop.stop)
            self.__thread.join()
        self.__is_active = False
