from __future__ import absolute_import

import time

import six

from ably import AblyException
from ably import AblyRest
from ably import Options

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase

test_vars = RestSetup.get_test_vars()


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestTime(BaseTestCase):

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    def test_time_accuracy(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_binary_protocol=self.use_binary_protocol)

        reported_time = ably.time()
        actual_time = time.time() * 1000.0

        seconds = 10
        self.assertLess(abs(actual_time - reported_time), seconds * 1000,
                msg="Time is not within %s seconds" % seconds)

    def test_time_without_key_or_token(self):
        ably = AblyRest(token='foo',
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        use_binary_protocol=self.use_binary_protocol)

        reported_time = ably.time()
        actual_time = time.time() * 1000.0

        seconds = 10
        self.assertLess(abs(actual_time - reported_time), seconds * 1000,
                msg="Time is not within %s seconds" % seconds)

    @dont_vary_protocol
    def test_time_fails_without_valid_host(self):
        ably = AblyRest(token='foo',
                        rest_host="this.host.does.not.exist",
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"])

        self.assertRaises(AblyException, ably.time)
