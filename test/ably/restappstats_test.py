from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import logging
import time
import unittest

from ably.exceptions import AblyException
from ably.rest import AblyRest

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestRestAppStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["encrypted"])
        time_from_service = cls.ably.time()
        cls.time_offset = time_from_service / 1000.0 - time.time()
        cls._test_infos = {}
        cls._publish(50)
        cls._publish(60)
        cls._publish(70)
        cls.sleep_for(timedelta(seconds=8))

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
    def _publish(cls, num_messages):
        channel_num = len(cls._test_infos)
        channel_name = 'appstats_%d' % channel_num
        cls.sleep_until_next_minute()
        interval_start = cls.server_now()
        channel = cls.ably.channels.get(channel_name)
        for i in range(num_messages):
            channel.publish('stats%d' % i, i)
        interval_end = cls.server_now()
        cls._test_infos[channel_name] = {
            "start": interval_start,
            "end": interval_end,
            "count": num_messages,
        }

    def _check_stats(self, first_channel, channel_count=1, direction='forwards',
            **kwargs):
        is_forwards = direction == 'forwards'
        last_channel = (first_channel + channel_count) if is_forwards else (first_channel - channel_count)
        r = range(first_channel, last_channel, 1 if is_forwards else -1)
        
        infos = [self.__class__._test_infos['appstats_%d' % i] for i in range]
        intervals = reduce(lambda x, y: {
            "start": min(x["start"], y["start"]),
            "end": max(x["end"], y["end"]),
        }, [{"start":e["start"],"end":e["end"]} for e in infos])

        kwargs["start"] = intervals['start']
        kwargs["end"] = intervals['end']
        kwargs["direction"] = direction

        stats = self.ably.stats(**kwargs)

        self.assertIsNotNone(stats, msg="Expected not-none stats")

        self.assertGreaterEqual(len(stats), 1, msg='Expected at least 1 record')
        self.assertLessEqual(len(stats), channel_count,
                msg='Expected up to %d records' % channel_count)

        # TODO Check expected messages and pagination
#        expected_messages = 0
#        for i in range(len(stats)):
#            c = self.__class__._test_infos['appstats_%d' % i]['count']
#            expected_messages += c

#        self.assertEquals(expected_messages, stats[0].inbound.all.all.count,
#                msg="Expected %d messages" % expected_messages)

    def test_check_minute_level_stats_exist_forwards(self):
        self._check_stats(0)

    def test_hour_level_stats_exist_forwards(self):
        self._check_stats(0, by='hour')

    def test_day_level_stats_exist_forwards(self):
        self._check_stats(0, by='day')

    def test_month_level_stats_exist_forwards(self):
        self._check_stats(0, by='month')

    def test_check_minute_level_stats_exist_backwards(self):
        self._check_stats(1, direction='backwards')

    def test_hour_level_stats_exist_backwards(self):
        self._check_stats(1, count=2, direction='backwards', by='hour')

    def test_day_level_stats_exist_backwards(self):
        self._check_stats(1, count=2, direction='backwards', by='day')

    def test_month_level_stats_exist_backwards(self):
        self._check_stats(1, count=2, direction='backwards', by='month')

    def test_check_limit_query_param_backwards(self):
        self._check_stats(2, count=3, direction='backwards', limit=1)

    def test_check_limit_query_param_forwards(self):
        self._check_stats(2, count=3, direction='forwards', limit=1)

    def test_check_query_pagination_backwards(self):
        self._check_stats(2, count=3, direction='backwards', limit=1)

    def test_check_query_pagination_forwards(self):
        self._check_stats(2, count=3, direction='forwards', limit=1)
