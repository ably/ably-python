import time

import pytest

from ably import AblyException

from test.ably.testapp import TestApp
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseAsyncTestCase


class TestRestTime(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    async def asyncSetUp(self):
        self.ably = await TestApp.get_ably_rest()

    async def asyncTearDown(self):
        await self.ably.close()

    async def test_time_accuracy(self):
        reported_time = await self.ably.time()
        actual_time = time.time() * 1000.0

        seconds = 10
        assert abs(actual_time - reported_time) < seconds * 1000, "Time is not within %s seconds" % seconds

    async def test_time_without_key_or_token(self):
        reported_time = await self.ably.time()
        actual_time = time.time() * 1000.0

        seconds = 10
        assert abs(actual_time - reported_time) < seconds * 1000, "Time is not within %s seconds" % seconds

    @dont_vary_protocol
    async def test_time_fails_without_valid_host(self):
        ably = await TestApp.get_ably_rest(key=None, token='foo', rest_host="this.host.does.not.exist")
        with pytest.raises(AblyException):
            await ably.time()

        await ably.close()
