# encoding: utf-8

from __future__ import absolute_import

from datetime import datetime, timedelta

import six
import msgpack
import responses

from ably import AblyRest
from ably.http.paginatedresult import PaginatedResult
from ably.types.presence import (PresenceMessage,
                                 make_encrypted_presence_response_handler)

from test.ably.utils import dont_vary_protocol, VaryByProtocolTestsMetaclass, BaseTestCase
from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestPresence(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])
        self.per_protocol_setup(True)

    def per_protocol_setup(self, use_binary_protocol):
        # This will be called every test that vary by protocol for each protocol
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.channel = self.ably.channels.get('persisted:presence_fixtures')

    def test_channel_presence_get(self):
        presence_page = self.channel.presence.get()
        self.assertIsInstance(presence_page, PaginatedResult)
        self.assertEqual(len(presence_page.items), 6)
        member = presence_page.items[0]
        self.assertIsInstance(member, PresenceMessage)
        self.assertTrue(member.action)
        self.assertTrue(member.id)
        self.assertTrue(member.client_id)
        self.assertTrue(member.data)
        self.assertTrue(member.connection_id)
        self.assertTrue(member.timestamp)

    def test_channel_presence_history(self):
        presence_history = self.channel.presence.history()
        self.assertIsInstance(presence_history, PaginatedResult)
        self.assertEqual(len(presence_history.items), 6)
        member = presence_history.items[0]
        self.assertIsInstance(member, PresenceMessage)
        self.assertTrue(member.action)
        self.assertTrue(member.id)
        self.assertTrue(member.client_id)
        self.assertTrue(member.data)
        self.assertTrue(member.connection_id)
        self.assertTrue(member.timestamp)
        self.assertTrue(member.encoding)

    def test_presence_get_encoded(self):
        presence_history = self.channel.presence.history()
        self.assertEqual(presence_history.items[-1].data, six.u("true"))
        self.assertEqual(presence_history.items[-2].data, six.u("24"))
        self.assertEqual(presence_history.items[-3].data,
                         six.u("This is a string clientData payload"))
        # this one doesn't have encoding field
        self.assertEqual(presence_history.items[-4].data,
                         six.u('{ "test": "This is a JSONObject clientData payload"}'))
        self.assertEqual(presence_history.items[-5].data,
                         {"example": {"json": "Object"}})

    def test_presence_history_encrypted(self):
        key = b'0123456789abcdef'
        self.ably.channels.release('persisted:presence_fixtures')
        self.channel = self.ably.channels.get('persisted:presence_fixtures',
                                              cipher={'key': key})
        presence_history = self.channel.presence.history()
        self.assertEqual(presence_history.items[0].data,
                         {'foo': 'bar'})

    def test_presence_get_encrypted(self):
        key = b'0123456789abcdef'
        self.ably.channels.release('persisted:presence_fixtures')
        self.channel = self.ably.channels.get('persisted:presence_fixtures',
                                              cipher={'key': key})
        presence_messages = self.channel.presence.get()
        message = list(filter(
            lambda message: message.client_id == 'client_encoded',
            presence_messages.items))[0]

        self.assertEqual(message.data, {'foo': 'bar'})

    def test_timestamp_is_datetime(self):
        presence_page = self.channel.presence.get()
        member = presence_page.items[0]
        self.assertIsInstance(member.timestamp, datetime)

    def test_presence_message_has_correct_member_key(self):
        presence_page = self.channel.presence.get()
        member = presence_page.items[0]

        self.assertEqual(member.member_key, "%s:%s" % (member.connection_id,
                                                       member.client_id))

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

    @dont_vary_protocol
    @responses.activate
    def test_get_presence_default_limit(self):
        url = self.presence_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.get()
        self.assertNotIn('limit=', responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_get_presence_with_limit(self):
        url = self.presence_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.get(300)
        self.assertIn('limit=300', responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_get_presence_max_limit_is_1000(self):
        url = self.presence_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.assertRaises(ValueError, self.channel.presence.get, 5000)

    @dont_vary_protocol
    @responses.activate
    def test_history_default_limit(self):
        url = self.history_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.history()
        self.assertNotIn('limit=', responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_history_with_limit(self):
        url = self.history_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.history(300)
        self.assertIn('limit=300', responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_history_with_direction(self):
        url = self.history_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.history(direction='backwards')
        self.assertIn('direction=backwards', responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_history_max_limit_is_1000(self):
        url = self.history_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.assertRaises(ValueError, self.channel.presence.history, 5000)

    @dont_vary_protocol
    @responses.activate
    def test_with_milisecond_start_end(self):
        url = self.history_mock_url()
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.history(start=100000, end=100001)
        self.assertIn('start=100000', responses.calls[0].request.url.split('?')[-1])
        self.assertIn('end=100001', responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_with_timedate_startend(self):
        url = self.history_mock_url()
        start = datetime(2015, 8, 15, 17, 11, 44, 706539)
        start_ms = 1439658704706
        end = start + timedelta(hours=1)
        end_ms = start_ms + (1000 * 60 * 60)
        self.responses_add_empty_msg_pack(url)
        self.channel.presence.history(start=start, end=end)
        self.assertIn('start=' + str(start_ms), responses.calls[0].request.url.split('?')[-1])
        self.assertIn('end=' + str(end_ms), responses.calls[0].request.url.split('?')[-1])

    @dont_vary_protocol
    @responses.activate
    def test_with_start_gt_end(self):
        url = self.history_mock_url()
        end = datetime(2015, 8, 15, 17, 11, 44, 706539)
        start = end + timedelta(hours=1)
        self.responses_add_empty_msg_pack(url)
        with self.assertRaisesRegexp(ValueError, "'end' parameter has to be greater than or equal to 'start'"):
            self.channel.presence.history(start=start, end=end)
