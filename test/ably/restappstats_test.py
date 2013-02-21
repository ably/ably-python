from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import time
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestAppStats(unittest.TestCase):
    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                rest_host=test_vars["rest_host"],
                rest_port=test_vars["rest_port"],
                encrypted=test_vars["encrypted"])

    def sleep_until_next_minute(self):
        one_second = timedelta(seconds=1)
        now = datetime.utcnow()
        next_minute = now.replace(second=0, microsecond=0) + one_second

        self.sleep_until(next_minute)

    def sleep_for(self, td):
        self.sleep_until(datetime.utcnow() + td)

    def sleep_until(self, until):
        now = datetime.utcnow()
        while now < until:
            dt = until - now
            time.sleep(dt.total_seconds())
            now = datetime.utcnow()

    def _check_stats(self, direction, channel_name):
        # sleep until next minute to prevent earlier test polluting results
        self.sleep_until_next_minute()
        interval_start = datetime.utcnow()

        # publish some messages
        channel = self.ably.channels.get(channel_name)
        for i in range(50):
            channel.publish("stats%d" % i, i)

        interval_end = time.time() * 1000.0

        # Wait for stats to be persisted
        self.sleep_for(timedelta(minutes=2))

        stats = self.ably.stats(direction=direction, 
                start=interval_start,
                end=interval_end)
        
        self.assertIsNotNone(stats, msg="Expected not-none stats")
        self.assertEquals(1, len(stats), msg="Expected 1 record")
        self.assertEquals(50, stats[0].inbound.all.all.count,
                msg="Expected 50 messages")

    def test_publish_events_and_check_stats_forwards(self):
        self._check_stats("forwards", "stats0")

    def test_publish_events_and_check_stats_backwards(self):
        self._check_stats("backwards", "stats1")

