from datetime import datetime
from datetime import timedelta
import logging

import pytest

from ably.types.stats import Stats
from ably.util.exceptions import AblyException
from ably.http.paginatedresult import PaginatedResult

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseAsyncTestCase

log = logging.getLogger(__name__)


class TestRestAppStatsSetup:
    __stats_added = False

    def get_params(self):
        return {
            'start': self.last_interval,
            'end': self.last_interval,
            'unit': 'minute',
            'limit': 1
        }

    async def asyncSetUp(self):
        self.ably = await RestSetup.get_ably_rest()
        self.ably_text = await RestSetup.get_ably_rest(use_binary_protocol=False)

        self.last_year = datetime.now().year - 1
        self.previous_year = datetime.now().year - 2
        self.last_interval = datetime(self.last_year, 2, 3, 15, 5)
        self.previous_interval = datetime(self.previous_year, 2, 3, 15, 5)
        previous_year_stats = 120
        stats = [
            {
                'intervalId': Stats.to_interval_id(self.last_interval - timedelta(minutes=2),
                                                   'minute'),
                'inbound': {'realtime': {'messages': {'count': 50, 'data': 5000}}},
                'outbound': {'realtime': {'messages': {'count': 20, 'data': 2000}}}
            },
            {
                'intervalId': Stats.to_interval_id(self.last_interval - timedelta(minutes=1),
                                                   'minute'),
                'inbound': {'realtime': {'messages': {'count': 60, 'data': 6000}}},
                'outbound': {'realtime': {'messages': {'count': 10, 'data': 1000}}}
            },
            {
                'intervalId': Stats.to_interval_id(self.last_interval, 'minute'),
                'inbound': {'realtime': {'messages': {'count': 70, 'data': 7000}}},
                'outbound': {'realtime': {'messages': {'count': 40, 'data': 4000}}},
                'persisted': {'presence': {'count': 20, 'data': 2000}},
                'connections': {'tls': {'peak': 20, 'opened': 10}},
                'channels': {'peak': 50, 'opened': 30},
                'apiRequests': {'succeeded': 50, 'failed': 10},
                'tokenRequests': {'succeeded': 60, 'failed': 20},
            }
        ]

        previous_stats = []
        for i in range(previous_year_stats):
            previous_stats.append(
                {
                    'intervalId': Stats.to_interval_id(self.previous_interval - timedelta(minutes=i),
                                                       'minute'),
                    'inbound': {'realtime': {'messages': {'count': i}}}
                }
            )
        # asynctest does not support setUpClass method
        if TestRestAppStatsSetup.__stats_added:
            return
        await self.ably.http.post('/stats', body=stats + previous_stats)
        TestRestAppStatsSetup.__stats_added = True

    async def asyncTearDown(self):
        await self.ably.close()
        await self.ably_text.close()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol


class TestDirectionForwards(TestRestAppStatsSetup, BaseAsyncTestCase,
                            metaclass=VaryByProtocolTestsMetaclass):

    def get_params(self):
        return {
            'start': self.last_interval - timedelta(minutes=2),
            'end': self.last_interval,
            'unit': 'minute',
            'direction': 'forwards',
            'limit': 1
        }

    async def test_stats_are_forward(self):
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.inbound.realtime.all.count == 50

    async def test_three_pages(self):
        stats_pages = await self.ably.stats(**self.get_params())
        assert not stats_pages.is_last()
        page2 = await stats_pages.next()
        page3 = await page2.next()
        assert page3.items[0].inbound.realtime.all.count == 70


class TestDirectionBackwards(TestRestAppStatsSetup, BaseAsyncTestCase,
                             metaclass=VaryByProtocolTestsMetaclass):

    def get_params(self):
        return {
            'end': self.last_interval,
            'unit': 'minute',
            'direction': 'backwards',
            'limit': 1
        }

    async def test_stats_are_forward(self):
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.inbound.realtime.all.count == 70

    async def test_three_pages(self):
        stats_pages = await self.ably.stats(**self.get_params())
        assert not stats_pages.is_last()
        page2 = await stats_pages.next()
        page3 = await page2.next()
        assert not stats_pages.is_last()
        assert page3.items[0].inbound.realtime.all.count == 50


class TestOnlyLastYear(TestRestAppStatsSetup, BaseAsyncTestCase,
                       metaclass=VaryByProtocolTestsMetaclass):

    def get_params(self):
        return {
            'end': self.last_interval,
            'unit': 'minute',
            'limit': 3
        }

    async def test_default_is_backwards(self):
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        assert stats[0].inbound.realtime.messages.count == 70
        assert stats[-1].inbound.realtime.messages.count == 50


class TestPreviousYear(TestRestAppStatsSetup, BaseAsyncTestCase,
                       metaclass=VaryByProtocolTestsMetaclass):

    def get_params(self):
        return {
            'end': self.previous_interval,
            'unit': 'minute',
        }

    async def test_default_100_pagination(self):
        self.stats_pages = await self.ably.stats(**self.get_params())
        stats = self.stats_pages.items
        assert len(stats) == 100
        next_page = await self.stats_pages.next()
        assert len(next_page.items) == 20


class TestRestAppStats(TestRestAppStatsSetup, BaseAsyncTestCase,
                       metaclass=VaryByProtocolTestsMetaclass):

    @dont_vary_protocol
    async def test_protocols(self):
        stats_pages = await self.ably.stats(**self.get_params())
        stats_pages1 = await self.ably_text.stats(**self.get_params())
        assert len(stats_pages.items) == len(stats_pages1.items)

    async def test_paginated_response(self):
        stats_pages = await self.ably.stats(**self.get_params())
        assert isinstance(stats_pages, PaginatedResult)
        assert isinstance(stats_pages.items[0], Stats)

    async def test_units(self):
        for unit in ['hour', 'day', 'month']:
            params = {
                'start': self.last_interval,
                'end': self.last_interval,
                'unit': unit,
                'direction': 'forwards',
                'limit': 1
            }
            stats_pages = await self.ably.stats(**params)
            stat = stats_pages.items[0]
            assert len(stats_pages.items) == 1
            assert stat.all.messages.count == 50 + 20 + 60 + 10 + 70 + 40
            assert stat.all.messages.data == 5000 + 2000 + 6000 + 1000 + 7000 + 4000

    @dont_vary_protocol
    async def test_when_argument_start_is_after_end(self):
        params = {
            'start': self.last_interval,
            'end': self.last_interval - timedelta(minutes=2),
            'unit': 'minute',
        }
        with pytest.raises(AblyException, match="'end' parameter has to be greater than or equal to 'start'"):
            await self.ably.stats(**params)

    @dont_vary_protocol
    async def test_when_limit_gt_1000(self):
        params = {
            'end': self.last_interval,
            'limit': 5000
        }
        with pytest.raises(AblyException, match="The maximum allowed limit is 1000"):
            await self.ably.stats(**params)

    async def test_no_arguments(self):
        params = {
            'end': self.last_interval,
        }
        stats_pages = await self.ably.stats(**params)
        self.stat = stats_pages.items[0]
        assert self.stat.interval_granularity == 'minute'

    async def test_got_1_record(self):
        stats_pages = await self.ably.stats(**self.get_params())
        assert 1 == len(stats_pages.items), "Expected 1 record"

    async def test_zero_by_default(self):
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.channels.refused == 0
        assert stat.outbound.webhook.all.count == 0

    async def test_return_aggregated_message_data(self):
        # returns aggregated message data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.all.messages.count == 70 + 40
        assert stat.all.messages.data == 7000 + 4000

    async def test_inbound_realtime_all_data(self):
        # returns inbound realtime all data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.inbound.realtime.all.count == 70
        assert stat.inbound.realtime.all.data == 7000

    async def test_inboud_realtime_message_data(self):
        # returns inbound realtime message data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.inbound.realtime.messages.count == 70
        assert stat.inbound.realtime.messages.data == 7000

    async def test_outbound_realtime_all_data(self):
        # returns outboud realtime all data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.outbound.realtime.all.count == 40
        assert stat.outbound.realtime.all.data == 4000

    async def test_persisted_data(self):
        # returns persisted presence all data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.persisted.all.count == 20
        assert stat.persisted.all.data == 2000

    async def test_connections_data(self):
        # returns connections all data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.connections.tls.peak == 20
        assert stat.connections.tls.opened == 10

    async def test_channels_all_data(self):
        # returns channels all data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.channels.peak == 50
        assert stat.channels.opened == 30

    async def test_api_requests_data(self):
        # returns api_requests data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.api_requests.succeeded == 50
        assert stat.api_requests.failed == 10

    async def test_token_requests(self):
        # returns token_requests data
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.token_requests.succeeded == 60
        assert stat.token_requests.failed == 20

    async def test_interval(self):
        # interval
        stats_pages = await self.ably.stats(**self.get_params())
        stats = stats_pages.items
        stat = stats[0]
        assert stat.interval_granularity == 'minute'
        assert stat.interval_id == self.last_interval.strftime('%Y-%m-%d:%H:%M')
        assert stat.interval_time == self.last_interval
