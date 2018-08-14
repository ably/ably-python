import pytest
from test.ably.restsetup import RestSetup


@pytest.fixture(scope='session', autouse=True)
def setup():
    RestSetup.get_test_vars()
    yield
    RestSetup.clear_test_vars()
