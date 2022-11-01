from pyee.asyncio import AsyncIOEventEmitter

from ably.util.helper import is_callable_or_coroutine

# pyee's event emitter doesn't support attaching a listener to all events
# so to patch it, we create a wrapper which uses two event emitters, one
# is used to listen to all events and this arbitrary string is the event name
# used to emit all events on that listener
_all_event = 'all'


def _is_named_event_args(*args):
    return len(args) == 2 and is_callable_or_coroutine(args[1])


def _is_all_event_args(*args):
    return len(args) == 1 and is_callable_or_coroutine(args[0])


class EventEmitter:
    def __init__(self):
        self.__named_event_emitter = AsyncIOEventEmitter()
        self.__all_event_emitter = AsyncIOEventEmitter()

    def on(self, *args):
        if _is_all_event_args(*args):
            self.__all_event_emitter.add_listener(_all_event, args[0])
        elif _is_named_event_args(*args):
            self.__named_event_emitter.add_listener(args[0], args[1])
        else:
            raise ValueError("EventEmitter.on(): invalid args")

    def once(self, *args):
        if _is_all_event_args(*args):
            self.__all_event_emitter.once(_all_event, args[0])
        elif _is_named_event_args(*args):
            self.__named_event_emitter.once(args[0], args[1])
        else:
            raise ValueError("EventEmitter.once(): invalid args")

    def off(self, *args):
        if len(args) == 0:
            self.__all_event_emitter.remove_all_listeners()
            self.__named_event_emitter.remove_all_listeners()
        elif _is_all_event_args(*args):
            self.__all_event_emitter.remove_listener(_all_event, args[0])
        elif _is_named_event_args(*args):
            self.__named_event_emitter.remove_listener(args[0], args[1])
        else:
            raise ValueError("EventEmitter.once(): invalid args")

    def _emit(self, *args):
        self.__named_event_emitter.emit(*args)
        self.__all_event_emitter.emit(_all_event, *args[1:])
