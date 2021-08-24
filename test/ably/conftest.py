import asyncio

import pytest
from test.ably.restsetup import RestSetup


@pytest.fixture(scope='session', autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(RestSetup.get_test_vars())
    yield loop
    loop.run_until_complete(RestSetup.clear_test_vars())
