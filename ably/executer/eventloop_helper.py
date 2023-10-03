from asyncio import events


def run(loop: events, coro):
    print("run")

def run_safe(loop: events, coro):
    print("run safe")

def run_sync(loop: events, coro):
    print("run sync")

def run_sync_safe(loop: events, coro):
    print("run sync safe")

def run_async(loop: events, coro):
    print("run async")

def run_async_safe(loop: events, coro):
    print("run async safe")
