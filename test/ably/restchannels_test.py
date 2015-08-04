from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import logging
import time
import collections
import unittest

import six
from six.moves import range

from ably import AblyException
from ably import AblyRest
from ably import Options
from ably.rest.channel import Channel, Channels

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestChannels(unittest.TestCase):

    def setUp(self):
        self.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                             host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"]))

    def test_rest_channels_attr(self):
        self.assertTrue(hasattr(self.ably, 'channels'))
        self.assertIsInstance(self.ably.channels, Channels)

    def test_channels_in(self):
        self.assertTrue('new_channel' not in self.ably.channels)
        self.ably.channels.get('new_channel')
        self.ably.channels.get('new_channel_2')
        self.assertTrue('new_channel' in self.ably.channels)
        self.assertTrue('new_channel_2' in self.ably.channels)

    def test_channels_iteration(self):
        channel_names = ['channel_{}'.format(i) for i in range(5)]
        [self.ably.channels.get(name) for name in channel_names]

        self.assertIsInstance(self.ably.channels, collections.Iterable)
        for name, channel in zip(channel_names, self.ably.channels):
            self.assertIsInstance(channel, Channel)
            self.assertEqual(name, channel.name)
