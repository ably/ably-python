from __future__ import absolute_import


from datetime import datetime
from datetime import timedelta
import logging

import six

from ably import AblyRest
from ably.types.stats import Stats
from ably.util.exceptions import AblyException
from ably.http.paginatedresult import PaginatedResult

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase

log = logging.getLogger(__name__)
test_vars = RestSetup.get_test_vars()


class TestRestAppStatsSetup(object):

    @classmethod
    def get_params(cls):
        return {
            'start': cls.last_interval,
            'end': cls.last_interval,
            'unit': 'minute',
            'limit': 1
        }

    @classmethod
    def setUpClass(cls):
        RestSetup._RestSetup__test_vars = None
        test_vars = RestSetup.get_test_vars()
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            rest_host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"])
        cls.ably_text = AblyRest(key=test_vars["keys"][0]["key_str"],
                                 rest_host=test_vars["host"],
                                 port=test_vars["port"],
                                 tls_port=test_vars["tls_port"],
                                 tls=test_vars["tls"],
                                 use_binary_protocol=False)

        cls.last_year = datetime.now().year - 1
        cls.previous_year = datetime.now().year - 2
        cls.last_interval = datetime(cls.last_year, 2, 3, 15, 5)
        cls.previous_interval = datetime(cls.previous_year, 2, 3, 15, 5)
        previous_year_stats = 120
        stats = [
            {
                'intervalId': Stats.to_interval_id(cls.last_interval -
                                                   timedelta(minutes=2),
                                                   'minute'),
                'inbound': {'realtime': {'messages': {'count': 50, 'data': 5000}}},
                'outbound': {'realtime': {'messages': {'count': 20, 'data': 2000}}}
            },
            {
                'intervalId': Stats.to_interval_id(cls.last_interval - timedelta(minutes=1),
                                                   'minute'),
                'inbound': {'realtime': {'messages': {'count': 60, 'data': 6000}}},
                'outbound': {'realtime': {'messages': {'count': 10, 'data': 1000}}}
            },
            {
                'intervalId': Stats.to_interval_id(cls.last_interval, 'minute'),
                'inbound': {'realtime': {'messages': {'count': 70, 'data': 7000}}},
                'outbound': {'realtime': {'messages': {'count': 40, 'data': 4000}}},
                'persisted': {'presence': {'count': 20, 'data': 2000}},
                'connections': {'tls':   {'peak': 20, 'opened': 10}},
                'channels': {'peak': 50, 'opened': 30},
                'apiRequests': {'succeeded': 50, 'failed': 10},
                'tokenRequests': {'succeeded': 60, 'failed': 20},
            }
        ]

        previous_stats = []
        for i in range(previous_year_stats):
            previous_stats.append(
                {
                    'intervalId': Stats.to_interval_id(cls.previous_interval -
                                                       timedelta(minutes=i),
                                                       'minute'),
                    'inbound':  {'realtime': {'messages': {'count': i}}}
                }
            )

        cls.ably.http.post('/stats', body=stats + previous_stats)

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.stats_pages = self.ably.stats(**self.get_params())
        self.stats = self.stats_pages.items
        self.stat = self.stats[0]


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestDirectionForwards(TestRestAppStatsSetup, BaseTestCase):

    @classmethod
    def get_params(cls):
        return {
            'start': cls.last_interval - timedelta(minutes=2),
            'end': cls.last_interval,
            'unit': 'minute',
            'direction': 'forwards',
            'limit': 1
        }

    def test_stats_are_forward(self):
        self.assertEqual(self.stat.inbound.realtime.all.count, 50)

    def test_three_pages(self):
        self.assertFalse(self.stats_pages.is_last())
        page3 = self.stats_pages.next().next()
        self.assertEqual(page3.items[0].inbound.realtime.all.count, 70)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestDirectionBackwards(TestRestAppStatsSetup, BaseTestCase):

    @classmethod
    def get_params(cls):
        return {
            'end': cls.last_interval,
            'unit': 'minute',
            'direction': 'backwards',
            'limit': 1
        }

    def test_stats_are_forward(self):
        self.assertEqual(self.stat.inbound.realtime.all.count, 70)

    def test_three_pages(self):
        self.assertFalse(self.stats_pages.is_last())
        page3 = self.stats_pages.next().next()
        self.assertEqual(page3.items[0].inbound.realtime.all.count, 50)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestOnlyLastYear(TestRestAppStatsSetup, BaseTestCase):

    @classmethod
    def get_params(cls):
        return {
            'end': cls.last_interval,
            'unit': 'minute',
            'limit': 3
        }

    def test_default_is_backwards(self):
        self.assertEqual(self.stats[0].inbound.realtime.messages.count, 70)
        self.assertEqual(self.stats[-1].inbound.realtime.messages.count, 50)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestPreviousYear(TestRestAppStatsSetup, BaseTestCase):

    @classmethod
    def get_params(cls):
        return {
            'end': cls.previous_interval,
            'unit': 'minute',
        }

    def test_default_100_pagination(self):
        self.assertEqual(len(self.stats), 100)
        next_page = self.stats_pages.next().items
        self.assertEqual(len(next_page), 20)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestAppStats(TestRestAppStatsSetup, BaseTestCase):

    @dont_vary_protocol
    def test_protocols(self):
        self.stats_pages = self.ably.stats(**self.get_params())
        self.stats_pages1 = self.ably_text.stats(**self.get_params())
        self.assertEqual(len(self.stats_pages.items),
                         len(self.stats_pages1.items))

    def test_paginated_response(self):
        self.assertIsInstance(self.stats_pages, PaginatedResult)
        self.assertIsInstance(self.stats_pages.items[0], Stats)

    def test_units(self):
        for unit in ['hour', 'day', 'month']:
            params = {
                'start': self.last_interval,
                'end': self.last_interval,
                'unit': unit,
                'direction': 'forwards',
                'limit': 1
            }
            stats_pages = self.ably.stats(**params)
            stat = stats_pages.items[0]
            self.assertEquals(len(stats_pages.items), 1)
            self.assertEqual(stat.all.messages.count,
                             50 + 20 + 60 + 10 + 70 + 40)
            self.assertEqual(stat.all.messages.data,
                             5000 + 2000 + 6000 + 1000 + 7000 + 4000)

    @dont_vary_protocol
    def test_when_argument_start_is_after_end(self):
        params = {
            'start': self.last_interval,
            'end': self.last_interval - timedelta(minutes=2),
            'unit': 'minute',
        }
        with self.assertRaisesRegexp(AblyException, "'end' parameter has to be greater than or equal to 'start'"):
            self.ably.stats(**params)

    @dont_vary_protocol
    def test_when_limit_gt_1000(self):
        params = {
            'end': self.last_interval,
            'limit': 5000
        }
        with self.assertRaisesRegexp(AblyException, "The maximum allowed limit is 1000"):
            self.ably.stats(**params)

    def test_no_arguments(self):
        params = {
            'end': self.last_interval,
        }
        self.stats_pages = self.ably.stats(**params)
        self.stat = self.stats_pages.items[0]
        self.assertEquals(self.stat.interval_granularity, 'minute')

    def test_got_1_record(self):
        self.assertEqual(1, len(self.stats_pages.items), "Expected 1 record")

    def test_zero_by_default(self):
        self.assertEqual(self.stat.channels.refused, 0)
        self.assertEqual(self.stat.outbound.webhook.all.count, 0)

    def test_return_aggregated_message_data(self):
        # returns aggregated message data
        self.assertEqual(self.stat.all.messages.count, 70 + 40)
        self.assertEqual(self.stat.all.messages.data, 7000 + 4000)

    def test_inbound_realtime_all_data(self):
        # returns inbound realtime all data
        self.assertEqual(self.stat.inbound.realtime.all.count, 70)
        self.assertEqual(self.stat.inbound.realtime.all.data, 7000)

    def test_inboud_realtime_message_data(self):
        # returns inbound realtime message data
        self.assertEqual(self.stat.inbound.realtime.messages.count, 70)
        self.assertEqual(self.stat.inbound.realtime.messages.data, 7000)

    def test_outbound_realtime_all_data(self):
        # returns outboud realtime all data
        self.assertEqual(self.stat.outbound.realtime.all.count, 40)
        self.assertEqual(self.stat.outbound.realtime.all.data, 4000)

    def test_persisted_data(self):
        # returns persisted presence all data
        self.assertEqual(self.stat.persisted.all.count, 20)
        self.assertEqual(self.stat.persisted.all.data, 2000)

    def test_connections_data(self):
        # returns connections all data
        self.assertEqual(self.stat.connections.tls.peak, 20)
        self.assertEqual(self.stat.connections.tls.opened, 10)

    def test_channels_all_data(self):
        # returns channels all data
        self.assertEqual(self.stat.channels.peak, 50)
        self.assertEqual(self.stat.channels.opened, 30)

    def test_api_requests_data(self):
        # returns api_requests data
        self.assertEqual(self.stat.api_requests.succeeded, 50)
        self.assertEqual(self.stat.api_requests.failed, 10)

    def test_token_requests(self):
        # returns token_requests data
        self.assertEqual(self.stat.token_requests.succeeded, 60)
        self.assertEqual(self.stat.token_requests.failed, 20)

    def test_inverval(self):
        # interval
        self.assertEqual(self.stat.interval_granularity, 'minute')
        self.assertEqual(self.stat.interval_id,
                         self.last_interval.strftime('%Y-%m-%d:%H:%M'))
        self.assertEqual(self.stat.interval_time, self.last_interval)
