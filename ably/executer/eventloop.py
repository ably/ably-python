import asyncio
import threading
from asyncio import events


class AblyEventLoop:
    loop: events = None
    thread: threading = None
    app: 'AblyEventLoop' = None

    def __init__(self):
        self.loop = None
        self.thread = None

    @staticmethod
    def current() -> 'AblyEventLoop':
        if (AblyEventLoop.app is None or
                AblyEventLoop.app.loop.is_closed()):
            AblyEventLoop.app = AblyEventLoop()
            AblyEventLoop.app.__create_if_not_exist()
        return AblyEventLoop.app

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
            # https://stackoverflow.com/questions/46093238/python-asyncio-event-loop-does-not-seem-to-stop-when-stop-method-is-called
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
            self.loop.close()
