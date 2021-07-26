import pytest
from test.ably.restsetup import RestSetup


@pytest.fixture(scope='session', autouse=True)
async def setup():
    await RestSetup.get_test_vars()
    yield
    await RestSetup.clear_test_vars()
