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
        if AblyEventLoop.__global_event_loop is None:
            AblyEventLoop.__global_event_loop = AblyEventLoop()
            AblyEventLoop.__global_event_loop.__create_if_not_exist()
        return AblyEventLoop.__global_event_loop

    def __create_if_not_exist(self):
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
        if not self.loop.is_running():
            self.thread = threading.Thread(
                target=self.loop.run_forever,
                daemon=True)
            self.thread.start()

    def close(self) -> events:
        self.loop.stop()
        self.loop.close()
        self.loop = None
        self.thread = None
