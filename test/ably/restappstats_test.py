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


    @classmethod
    def server_now(cls):
        return datetime.fromtimestamp(cls.time_offset + time.time())


    @classmethod
    def _publish(cls, num_messages, channel_name):
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


    def test_posted_stats(self):
        stats_pages = TestRestAppStats.ably.stats(SearchParams(backwards=False))#, start=TestRestAppStats.interval_start, end=TestRestAppStats.interval_end))
        stats_page = stats_pages.current
        stats0 = stats_page[0]
        self.assertEqual(4, len(stats_page), "Expected 4 records")
        self.assertEqual(50, stats_page[0].all.all.count, "Expected 50 messages")
