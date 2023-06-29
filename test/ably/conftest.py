import asyncio

import pytest
from test.ably.testapp import TestApp


@pytest.fixture(scope='session', autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(TestApp.get_test_vars())
    yield loop
    loop.run_until_complete(TestApp.clear_test_vars())
