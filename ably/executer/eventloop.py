import asyncio
import threading
from asyncio import events


class AppEventLoop:
    loop: events = None
    thread: threading = None
    active: 'AppEventLoop' = None

    def __init__(self):
        self.loop = None
        self.thread = None

    @staticmethod
    def current() -> 'AppEventLoop':
        if (AppEventLoop.active is None or
                AppEventLoop.active.loop.is_closed()):
            AppEventLoop.active = AppEventLoop()
            AppEventLoop.active.__create_if_not_exist()
        return AppEventLoop.active

    def __create_if_not_exist(self):
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
        if not self.loop.is_running():
            self.thread = threading.Thread(
                target=self.loop.run_forever,
                daemon=True)
            self.thread.start()

    def close(self) -> events:
        if self.loop is not None and not self.loop.is_closed:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
            self.loop.close()
