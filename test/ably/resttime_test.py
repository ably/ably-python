import time

import pytest

from ably import AblyException

from test.ably.restsetup import RestSetup


@pytest.mark.asyncio
async def test_time_accuracy(rest):
    reported_time = await rest.time()
    actual_time = time.time() * 1000.0

    seconds = 10
    assert abs(actual_time - reported_time) < seconds * 1000, "Time is not within %s seconds" % seconds


@pytest.mark.asyncio
async def test_time_without_key_or_token(rest):
    reported_time = await rest.time()
    actual_time = time.time() * 1000.0

    seconds = 10
    assert abs(actual_time - reported_time) < seconds * 1000, "Time is not within %s seconds" % seconds


@pytest.mark.asyncio
async def test_time_fails_without_valid_host():
    ably = await RestSetup.get_ably_rest(key=None, token='foo', rest_host="this.host.does.not.exist")
    with pytest.raises(AblyException):
        await ably.time()

    await ably.close()
