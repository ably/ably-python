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
from ably.types.searchparams import SearchParams
from ably.http.httputils import HttpUtils


from test.ably.restsetup import RestSetup
log = logging.getLogger(__name__)
test_vars = RestSetup.get_test_vars()
log.debug("KEY init: "+test_vars["keys"][0]["key_str"])


class TestRestAppStats(unittest.TestCase):
    test_start = 0
    interval_start = 0
    interval_end = 0



    @classmethod
    def setUpClass(cls):
        log.debug("KEY class: "+test_vars["keys"][0]["key_str"])
        log.debug("TLS: "+str(test_vars["tls"]))
        cls.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                restHost=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"]))
        time_from_service = cls.ably.time()
        cls.time_offset = time_from_service / 1000.0 - time.time()
        cls._publishTestStats()

        #cls._test_infos = {}
        #cls._publish(50)
        #cls._publish(60)
        #cls._publish(70)
        #cls.sleep_for(timedelta(seconds=8))

    @classmethod
    def server_now(cls):
        return datetime.fromtimestamp(cls.time_offset + time.time())


#TODO RM
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
       # cls.sleep_until_next_minute()
        cls.interval_start = cls.server_now()

        if not cls.test_start:
            cls.test_start = cls.interval_start
        channel = cls.ably.channels.get(channel_name)
        for i in range(num_messages):
            channel.publish('stats%d' % i, i)

        cls.interval_end = cls.server_now()
        cls.sleep_for(timedelta(seconds=8))




         
    @classmethod
    def _publishTestStats(cls):
        stats_text='''[{"intervalId": "2015-03-13:05:22", "inbound": { "realtime": {"messages":{ "count":50,"data":5000}}}},
        {"intervalId": "2015-03-13:05:31", "inbound": { "realtime": {"messages":{ "count":50,"data":5000}}}},
        {"intervalId": "2015-03-13:15:20", "inbound": { "realtime": {"messages":{ "count":50,"data":5000}}}},
        {"intervalId": "2015-03-16:03:17", "inbound": { "realtime": {"messages":{ "count":50,"data":5000}}}}]'''
        r = cls.ably.http.post("/stats", headers=HttpUtils.default_post_headers(),
                    body=stats_text)
        AblyException.raise_for_response(r)


    def test_app_stats_01_minute_level_forwards(self):
        #TestRestAppStats._publish(50, 'appstats_0')

        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False))#, start=TestRestAppStats.interval_start, end=TestRestAppStats.interval_end))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

    def test_app_stats_02_hour_level_forwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False, start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, unit=SearchParams.Unit.HOUR))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

    def test_app_stats_03_day_level_forwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False, start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, unit=SearchParams.Unit.DAY))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

    def test_app_stats_04_month_level_forwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False, start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, unit=SearchParams.Unit.MONTH))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

    def test_app_stats_05_minute_level_backwards(self):
        TestRestAppStats._publish(60, 'appstats_1')
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

    def test_app_stats_06_hour_level_backwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, unit=SearchParams.Unit.HOUR))
        stats_page = stats_pages.current

        self.assertTrue(1 == len(stats_page) or 2 == len(stats_page), "Expected 1 or 2 records")
        if (1 == len(stats_page)):
            self.assertEqual(110, stats_page[0].inbound.all.all.count, "Expected 110 messages")
        else:
            self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")
        

    def test_app_stats_07_day_level_backwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, unit=SearchParams.Unit.DAY))
        stats_page = stats_pages.current

        self.assertTrue(1 == len(stats_page) or 2 == len(stats_page), "Expected 1 or 2 records")
        if (1 == len(stats_page)):
            self.assertEqual(110, stats_page[0].inbound.all.all.count, "Expected 110 messages")
        else:
            self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

    def test_app_stats_08_month_level_backwards(self):
        
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, unit=SearchParams.Unit.MONTH))
        stats_page = stats_pages.current

        self.assertTrue(1 == len(stats_page) or 2 == len(stats_page), "Expected 1 or 2 records")
        if (1 == len(stats_page)):
            self.assertEqual(110, stats_page[0].inbound.all.all.count, "Expected 110 messages")
        else:
            self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

    def test_app_stats_09_limit_backwards(self):
        TestRestAppStats._publish(70, 'appstats_2')
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, limit=1))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(70, stats_page[0].inbound.all.all.count, "Expected 70 messages")

    def test_app_stats_10_limit_forwards(self):
        
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, limit=1))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

    def test_app_stats_11_pagination_backwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, limit=1))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(70, stats_page[0].inbound.all.all.count, "Expected 70 messages")

        self.assertTrue(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

        self.assertTrue(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

        self.assertFalse(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        self.assertIsNone(stats_pages, "Expected None")

    def test_app_stats_12_pagination_forwards(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, limit=1))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

        self.assertTrue(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

        self.assertTrue(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(70, stats_page[0].inbound.all.all.count, "Expected 70 messages")

        self.assertFalse(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        self.assertIsNone(stats_pages, "Expected None")

    def test_app_stats_13_pagination_backwards_get_first(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, limit=1))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(70, stats_page[0].inbound.all.all.count, "Expected 70 messages")

        self.assertTrue(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

        self.assertTrue(stats_pages.has_first)
        stats_pages = stats_pages.get_first()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(70, stats_page[0].inbound.all.all.count, "Expected 70 messages")

    def test_app_stats_14_pagination_forwards_get_first(self):
        
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=True,start=TestRestAppStats.interval_start,end=TestRestAppStats.interval_end, limit=1))
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")

        self.assertTrue(stats_pages.has_next)
        stats_pages = stats_pages.get_next()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(60, stats_page[0].inbound.all.all.count, "Expected 60 messages")

        self.assertTrue(stats_pages.has_first)
        stats_pages = stats_pages.get_first()
        stats_page = stats_pages.current

        self.assertEqual(1, len(stats_page), "Expected 1 record")
        self.assertEqual(50, stats_page[0].inbound.all.all.count, "Expected 50 messages")\


    def test_posted_stats(self):

       # TestRestAppStats._publishTestStats()
        print ("TODO")
