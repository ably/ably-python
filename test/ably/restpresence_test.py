from __future__ import absolute_import

import unittest
from datetime import datetime, timedelta

import responses

from ably import AblyRest
from ably.http.paginatedresult import PaginatedResult
from ably.types.presence import PresenceMessage

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestPresence(unittest.TestCase):

    def setUp(self):
        self.ably = AblyRest(test_vars["keys"][0]["key_str"],
                             host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])
        self.channel = self.ably.channels.get('persisted:presence_fixtures')

    def test_channel_presence_get(self):
        presence_page = self.channel.presence.get()
        self.assertIsInstance(presence_page, PaginatedResult)
        self.assertEqual(len(presence_page.items), 6)
        member = presence_page.items[0]
        self.assertTrue(isinstance(member, PresenceMessage))
        self.assertTrue(member.action)
        self.assertTrue(member.client_id)
        self.assertTrue(member.client_data)
        self.assertTrue(member.connection_id)
        self.assertTrue(member.timestamp)

    def test_channel_presence_history(self):
        presence_history = self.channel.presence.history()
        self.assertIsInstance(presence_history, PaginatedResult)
        self.assertEqual(len(presence_history.items), 6)
        member = presence_history.items[0]
        self.assertTrue(isinstance(member, PresenceMessage))
        self.assertTrue(member.action)
        self.assertTrue(member.client_id)
        self.assertTrue(member.client_data)
        self.assertTrue(member.connection_id)
        self.assertTrue(member.timestamp)

    def presence_mock_url(self):
        kwargs = {
            'scheme': 'https' if test_vars['tls'] else 'http',
            'host': test_vars['host']
        }
        port = test_vars['tls_port'] if test_vars.get('tls') else kwargs['port']
        if port == 80:
            kwargs['port_sufix'] = ''
        else:
            kwargs['port_sufix'] = ':' + str(port)
        url = '{scheme}://{host}{port_sufix}/channels/persisted%3Apresence_fixtures/presence'
        return url.format(**kwargs)

    def history_mock_url(self):
        kwargs = {
            'scheme': 'https' if test_vars['tls'] else 'http',
            'host': test_vars['host']
        }
        port = test_vars['tls_port'] if test_vars.get('tls') else kwargs['port']
        if port == 80:
            kwargs['port_sufix'] = ''
        else:
            kwargs['port_sufix'] = ':' + str(port)
        url = '{scheme}://{host}{port_sufix}/channels/persisted%3Apresence_fixtures/presence/history'
        return url.format(**kwargs)


    @responses.activate
    def test_get_presence_default_limit(self):
        url = self.presence_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.get()
        self.assertNotIn('limit=', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_get_presence_with_limit(self):
        url = self.presence_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.get(300)
        self.assertIn('limit=300', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_get_presence_max_limit_is_1000(self):
        url = self.presence_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.get(5000)
        self.assertIn('limit=1000', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_history_default_limit(self):
        url = self.history_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.history()
        self.assertNotIn('limit=', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_history_with_limit(self):
        url = self.history_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.history(300)
        self.assertIn('limit=300', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_history_with_direction(self):
        url = self.history_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.history(direction='backwards')
        self.assertIn('direction=backwards', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_history_max_limit_is_1000(self):
        url = self.history_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.history(5000)
        self.assertIn('limit=1000', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_with_milisecond_start_end(self):
        url = self.history_mock_url()
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.history(start=100000, end=100001)
        self.assertIn('start=100000', responses.calls[0].request.url.split('?')[-1])
        self.assertIn('end=100001', responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_with_timedate_startend(self):
        url = self.history_mock_url()
        start = datetime(2015, 8, 15, 17, 11, 44, 706539)
        start_ms = 1439658704706
        end = start + timedelta(hours=1)
        end_ms = start_ms + (1000 * 60 * 60)
        responses.add(responses.GET, url, body='{}')
        self.channel.presence.history(start=start, end=end)
        self.assertIn('start=' + str(start_ms), responses.calls[0].request.url.split('?')[-1])
        self.assertIn('end=' + str(end_ms), responses.calls[0].request.url.split('?')[-1])

    @responses.activate
    def test_with_start_gt_end(self):
        url = self.history_mock_url()
        end = datetime(2015, 8, 15, 17, 11, 44, 706539)
        start = end + timedelta(hours=1)
        responses.add(responses.GET, url, body='{}')
        with self.assertRaisesRegexp(ValueError, "'end' parameter has to be greater than or equal to 'start'"):
            self.channel.presence.history(start=start, end=end)
