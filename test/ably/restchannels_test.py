from __future__ import absolute_import

import collections

from six.moves import range

from ably import AblyRest, AblyException
from ably.rest.channel import Channel, Channels, Presence
from ably.types.capability import Capability
from ably.util.crypto import generate_random_key

from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase

test_vars = RestSetup.get_test_vars()


# makes no request, no need to use different protocols
class TestChannels(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

    def test_rest_channels_attr(self):
        self.assertTrue(hasattr(self.ably, 'channels'))
        self.assertIsInstance(self.ably.channels, Channels)

    def test_channels_get_returns_new_or_existing(self):
        channel = self.ably.channels.get('new_channel')
        self.assertIsInstance(channel, Channel)
        channel_same = self.ably.channels.get('new_channel')
        self.assertIs(channel, channel_same)

    def test_channels_get_returns_new_with_options(self):
        key = generate_random_key()
        channel = self.ably.channels.get('new_channel', cipher={'key': key})
        self.assertIsInstance(channel, Channel)
        self.assertIs(channel.cipher.secret_key, key)

    def test_channels_get_updates_existing_with_options(self):
        key = generate_random_key()
        channel = self.ably.channels.get('new_channel', cipher={'key': key})
        self.assertIsNot(channel.cipher, None)

        channel_same = self.ably.channels.get('new_channel', cipher=None)
        self.assertIs(channel, channel_same)
        self.assertIs(channel.cipher, None)

    def test_channels_get_doesnt_updates_existing_with_none_options(self):
        key = generate_random_key()
        channel = self.ably.channels.get('new_channel', cipher={'key': key})
        self.assertIsNot(channel.cipher, None)

        channel_same = self.ably.channels.get('new_channel')
        self.assertIs(channel, channel_same)
        self.assertIsNot(channel.cipher, None)

    def test_channels_in(self):
        self.assertTrue('new_channel' not in self.ably.channels)
        self.ably.channels.get('new_channel')
        new_channel_2 = self.ably.channels.get('new_channel_2')
        self.assertTrue('new_channel' in self.ably.channels)
        self.assertTrue(new_channel_2 in self.ably.channels)

    def test_channels_iteration(self):
        channel_names = ['channel_{}'.format(i) for i in range(5)]
        [self.ably.channels.get(name) for name in channel_names]

        self.assertIsInstance(self.ably.channels, collections.Iterable)
        for name, channel in zip(channel_names, self.ably.channels):
            self.assertIsInstance(channel, Channel)
            self.assertEqual(name, channel.name)

    def test_channels_release(self):
        self.ably.channels.get('new_channel')
        self.ably.channels.release('new_channel')

        with self.assertRaises(KeyError):
            self.ably.channels.release('new_channel')

    def test_channels_del(self):
        self.ably.channels.get('new_channel')
        del self.ably.channels['new_channel']

        with self.assertRaises(KeyError):
            del self.ably.channels['new_channel']

    def test_channel_has_presence(self):
        channel = self.ably.channels.get('new_channnel')
        self.assertTrue(channel.presence)
        self.assertTrue(isinstance(channel.presence, Presence))

    def test_without_permissions(self):
        key = test_vars["keys"][2]
        ably = AblyRest(key=key["key_str"],
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"])
        with self.assertRaises(AblyException) as cm:
            ably.channels['test_publish_without_permission'].publish('foo', 'woop')

        the_exception = cm.exception
        self.assertIn('not permitted', the_exception.message)
