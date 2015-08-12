from __future__ import absolute_import

import unittest

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
        self.assertTrue(member.member_id)
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
        self.assertTrue(member.member_id)
        self.assertTrue(member.client_data)
        self.assertTrue(member.connection_id)
        self.assertTrue(member.timestamp)
