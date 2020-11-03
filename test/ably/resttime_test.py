import time

import pytest

from ably import AblyException

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase


class TestRestTime(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    def test_time_accuracy(self):
        ably = RestSetup.get_ably_rest(use_binary_protocol=self.use_binary_protocol)

        reported_time = ably.time()
        actual_time = time.time() * 1000.0

        seconds = 10
        assert abs(actual_time - reported_time) < seconds * 1000, "Time is not within %s seconds" % seconds

    def test_time_without_key_or_token(self):
        ably = RestSetup.get_ably_rest(key=None, token='foo',
                                       use_binary_protocol=self.use_binary_protocol)

        reported_time = ably.time()
        actual_time = time.time() * 1000.0

        seconds = 10
        assert abs(actual_time - reported_time) < seconds * 1000, "Time is not within %s seconds" % seconds

    @dont_vary_protocol
    def test_time_fails_without_valid_host(self):
        ably = RestSetup.get_ably_rest(key=None, token='foo', rest_host="this.host.does.not.exist")
        with pytest.raises(AblyException):
            ably.time()
