import asyncio
import threading
from asyncio import events


class AblyEventLoop:
    loop: events = None
    thread: threading = None
    __global_event_loop: 'AblyEventLoop' = None

    def __init__(self):
        self.loop = None
        self.thread = None

    @staticmethod
    def get_global() -> 'AblyEventLoop':
        if (AblyEventLoop.__global_event_loop is None or
                AblyEventLoop.__global_event_loop.loop.is_closed()):
            AblyEventLoop.__global_event_loop = AblyEventLoop()
            AblyEventLoop.__global_event_loop.__create_if_not_exist()
        return AblyEventLoop.__global_event_loop

    def __create_if_not_exist(self):
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
        if not self.loop.is_running():
            self.thread = threading.Thread(
                target=self.loop.run_forever,
                daemon=True)
            self.thread.start()

    def close(self) -> events:
        # https://stackoverflow.com/questions/46093238/python-asyncio-event-loop-does-not-seem-to-stop-when-stop-method-is-called
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.loop.close()
