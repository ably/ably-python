import asyncio
import threading
from asyncio import events


class AppEventLoop:
    loop: events
    thread: threading
    _global: 'AppEventLoop' = None
    is_active: bool

    def __init__(self):
        self.loop = None
        self.thread = None
        self.is_active = False

    @staticmethod
    def current() -> 'AppEventLoop':
        if AppEventLoop._global is None or not AppEventLoop._global.is_active:
            AppEventLoop._global = AppEventLoop()
            AppEventLoop._global.create_safe()
        return AppEventLoop._global

    def create_safe(self):
        if self.is_active:
            self.close()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()
        self.is_active = True

    def close(self) -> events:
        if self.loop is not None and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread is not None:
            self.thread.join()
        self.is_active = False
