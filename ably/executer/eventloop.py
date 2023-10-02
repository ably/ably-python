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
            AppEventLoop._global = AppEventLoop.create()
        return AppEventLoop._global

    @staticmethod
    def create() -> 'AppEventLoop':
        app_loop = AppEventLoop()
        app_loop.loop = asyncio.new_event_loop()
        app_loop.thread = threading.Thread(target=app_loop.loop.run_forever)
        app_loop.thread.start()
        app_loop.is_active = True
        return app_loop

    def close(self) -> events:
        if self.loop is not None and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread is not None:
            self.thread.join()
        self.is_active = False
