# encoding: utf-8

from __future__ import absolute_import

import json
import unittest
from datetime import datetime, timedelta
from functools import wraps

import six
import mock
import msgpack
import responses

from ably import AblyRest
from ably.http.paginatedresult import PaginatedResult
from ably.types.presence import (PresenceMessage, make_presence_response_handler,
                                 make_encrypted_presence_response_handler)
from ably import ChannelOptions
from ably.util.crypto import get_default_params

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


def assert_responses_types(types):
    """
    This code is a bit complicated but saves a lot of coding.
    It is a decorator to check if we retrieved presence with the correct protocol.
    usage:

    @assert_responses_types(['json', 'msgpack'])
    def test_something(self):
        ...

    this will check if we receive two responses, the first using json and the
    second msgpack
    """
    responses = []

    def presence_side_effect(binary):
        def handler(response):
            responses.append(response)
            return make_presence_response_handler(binary)(response)
        return handler

    def encrypted_side_effect(cipher, binary):
        def handler(response):
            responses.append(response)
            return make_encrypted_presence_response_handler(cipher, binary)(response)
        return handler

    def patch_handlers():
            p1 = mock.patch('ably.types.presence.make_presence_response_handler',
                            side_effect=presence_side_effect)
            p2 = mock.patch('ably.types.presence.make_encrypted_presence_response_handler',
                            side_effect=encrypted_side_effect)
            p1.start()
            p2.start()
            return p1, p2

    def unpatch_handlers(patchers):
        for patcher in patchers:
            patcher.stop()

    def test_decorator(fn):
        @wraps(fn)
        def test_decorated(self, *args, **kwargs):
            patchers = patch_handlers()
            fn(self, *args, **kwargs)
            unpatch_handlers(patchers)
            self.assertEquals(len(types), len(responses))
            for type_name, response in zip(types, responses):
                if type_name == 'json':
                    self.assertEquals(response.headers['content-type'], 'application/json')
                    json.loads(response.text)
                else:
                    self.assertEquals(response.headers['content-type'], 'application/x-msgpack')
                    msgpack.unpackb(response.content, encoding='utf-8')

        return test_decorated
    return test_decorator


class TestPresence(unittest.TestCase):

    def setUp(self):
        self.ably = AblyRest(test_vars["keys"][0]["key_str"],
                             host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])
        self.ably_bin = AblyRest(test_vars["keys"][0]["key_str"],
                                 host=test_vars["host"],
                                 port=test_vars["port"],
                                 tls_port=test_vars["tls_port"],
                                 tls=test_vars["tls"],
                                 use_text_protocol=False)
        self.channel = self.ably.channels.get('persisted:presence_fixtures')
        self.channel_bin = self.ably_bin.channels.get('persisted:presence_fixtures')
        self.channels = [self.channel, self.channel_bin]

    @assert_responses_types(['json', 'msgpack'])
    def test_channel_presence_get(self):
        for channel in self.channels:
            presence_page = channel.presence.get()
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

    @assert_responses_types(['json', 'msgpack'])
    def test_channel_presence_history(self):
        for channel in self.channels:
            presence_history = channel.presence.history()
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

    @assert_responses_types(['json', 'msgpack'])
    def test_presence_get_encoded(self):
        for channel in self.channels:
            presence_history = channel.presence.history()
            self.assertEqual(presence_history.items[-1].data, six.u("true"))
            self.assertEqual(presence_history.items[-2].data, six.u("24"))
            self.assertEqual(presence_history.items[-3].data,
                             six.u("This is a string clientData payload"))
            # this one doesn't have encoding field
            self.assertEqual(presence_history.items[-4].data,
                             six.u('{ "test": "This is a JSONObject clientData payload"}'))
            self.assertEqual(presence_history.items[-5].data,
                             {"example": {"json": "Object"}})

    @assert_responses_types(['json', 'msgpack'])
    def test_presence_history_encrypted(self):
        for use_text_protocol in [True, False]:
            ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"],
                            use_text_protocol=use_text_protocol)
            params = get_default_params('0123456789abcdef')
            self.channel = ably.channels.get('persisted:presence_fixtures',
                                             options=ChannelOptions(
                                                encrypted=True,
                                                cipher_params=params))
            presence_history = self.channel.presence.history()
            self.assertEqual(presence_history.items[0].data,
                             {'foo': 'bar'})

    @assert_responses_types(['json', 'msgpack'])
    def test_presence_get_encrypted(self):
        for use_text_protocol in [True, False]:
            ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                            host=test_vars["host"],
                            port=test_vars["port"],
                            tls_port=test_vars["tls_port"],
                            tls=test_vars["tls"],
                            use_text_protocol=use_text_protocol)
            params = get_default_params('0123456789abcdef')
            self.channel = ably.channels.get('persisted:presence_fixtures',
                                             options=ChannelOptions(
                                                encrypted=True,
                                                cipher_params=params))
            presence_messages = self.channel.presence.get()
            message = list(filter(
                lambda message: message.client_id == 'client_encoded',
                presence_messages.items))[0]

            self.assertEqual(message.data, {'foo': 'bar'})

    @assert_responses_types(['json'])
    def test_timestamp_is_datetime(self):
        presence_page = self.channel.presence.get()
        member = presence_page.items[0]
        self.assertIsInstance(member.timestamp, datetime)

    @assert_responses_types(['json'])
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
        self.assertRaises(ValueError, self.channel.presence.get, 5000)

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
        self.assertRaises(ValueError, self.channel.presence.history, 5000)

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
