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


@pytest_asyncio.fixture(name="new_rest")
async def new_rest_fixture():
    async def rest_factory(**kwargs):
        ably = await RestSetup.get_ably_rest(**kwargs)
        return ably

    yield rest_factory


@pytest_asyncio.fixture(scope='session')
async def test_vars():
    result = await RestSetup.get_test_vars()
    yield result
    await RestSetup.clear_test_vars()


@pytest_asyncio.fixture(name="json_rest")
async def json_rest_fixture(new_rest):
    ably = await new_rest(use_binary_protocol=False)
    yield ably
    await ably.close()


@pytest_asyncio.fixture(name="msgpack_rest")
async def msgpack_rest_fixture(new_rest):
    ably = await new_rest(use_binary_protocol=True)
    yield ably
    await ably.close()
