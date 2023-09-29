import asyncio
import threading
from asyncio import events
from threading import Thread


class AblyEventLoop:
    eventloop: events
    eventloopThread: Thread

    @staticmethod
    def new_instance():
         AblyEventLoop()

    # Create a new loop and start it on a new thread
    # Start a new thread first and then run loop forever inside it
    # This will make sure, loop is not running on the external thread.
    # Inside the newly created thread, we can use asyncio.set_event_loop(loop)
    def create_if_not_exist(self):
        if self.eventloop is None:
            self.eventloop = asyncio.new_event_loop()
        if not self.eventloop.is_running():
            self.eventloopThread = threading.Thread(
                target=self.eventloop.run_forever,
                daemon=True)
            self.eventloopThread.start()
    def get(self) -> events:
        return self.eventloop

    def stop(self) -> events:
        self.eventloop.stop()
    def close(self) -> events:
        self.stop()
        self.eventloop.close()
        self.eventloop = None
        self.eventloopThread = None

    def __int__(self, loop):
        print("Hello")