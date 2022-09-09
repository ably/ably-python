import asyncio

import pytest
import pytest_asyncio
from test.ably.restsetup import RestSetup


@pytest.fixture(scope='session', autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(RestSetup.get_test_vars())
    yield loop
    loop.run_until_complete(RestSetup.clear_test_vars())


@pytest_asyncio.fixture(params=["json", "msgpack"])
async def rest(request):
    protocol = request.param
    use_binary_protocol = protocol == "msgpack"
    ably = await RestSetup.get_ably_rest(use_binary_protocol=use_binary_protocol)
    yield ably
    await ably.close()
