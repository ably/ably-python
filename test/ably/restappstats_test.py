from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import logging
import time
import unittest

from ably import AblyException
from ably import AblyRest
from ably import Options

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestRestAppStats(unittest.TestCase):
    test_start = 0
    interval_start = 0
    interval_end = 0

    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"]))
        time_from_service = cls.ably.time()
        cls.time_offset = time_from_service / 1000.0 - time.time()

        #cls._test_infos = {}
        #cls._publish(50)
        #cls._publish(60)
        #cls._publish(70)
        #cls.sleep_for(timedelta(seconds=8))

    @classmethod
    def server_now(cls):
        return datetime.fromtimestamp(cls.time_offset + time.time())

    @classmethod
    def sleep_until_next_minute(cls):
        server_now = cls.server_now()
        one_minute = timedelta(minutes=1)
        next_minute = server_now + one_minute
        next_minute = next_minute.replace(second=0, microsecond=0)

        cls.sleep_for(next_minute - server_now)

    @classmethod
    def sleep_for(cls, td):
        cls.sleep_until(datetime.utcnow() + td)

    @staticmethod
    def sleep_until(until):
        now = datetime.utcnow()
        while now < until:
            dt = until - now
            time.sleep(dt.total_seconds())
            now = datetime.utcnow()

    @classmethod
    def _publish(cls, num_messages, channel_name):
        cls.sleep_until_next_minute()
        cls.interval_start = cls.server_now()

        if not cls.test_start:
            cls.test_start = cls.interval_start

        channel = cls.ably.channels.get(channel_name)
        for i in range(num_messages):
            channel.publish('stats%d' % i, i)

        cls.interval_end = cls.server_now()

        cls.sleep_for(timedelta(seconds=8))

    def test_app_stats_01_minute_level_forwards(self):
        TestRestAppStats._publish(50, 'appstats_0')
        params = {
            'direction': 'forwards',
            'start': TestRestAppStats.interval_start,
            'end': TestRestAppStats.interval_end,
        }
        stats_pages = TestRestAppStats.ably.stats(**params)
        stats_page = stats_pages.current
        log.debug(stats_page[0])

        self.assertEquals(1, len(stats_page), "Expected 1 record")
        self.assertEquals(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")
