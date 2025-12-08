import pytest_asyncio

from test.ably.testapp import TestApp


@pytest_asyncio.fixture(scope='session', autouse=True)
async def test_app_setup():
    await TestApp.get_test_vars()
    yield
    await TestApp.clear_test_vars()
