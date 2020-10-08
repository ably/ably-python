from collections.abc import Iterable

import pytest

from ably import AblyException
from ably.rest.channel import Channel, Channels, Presence
from ably.util.crypto import generate_random_key

from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase

test_vars = RestSetup.get_test_vars()


# makes no request, no need to use different protocols
class TestChannels(BaseTestCase):

    def setUp(self):
        self.ably = RestSetup.get_ably_rest()

    def test_rest_channels_attr(self):
        assert hasattr(self.ably, 'channels')
        assert isinstance(self.ably.channels, Channels)

    def test_channels_get_returns_new_or_existing(self):
        channel = self.ably.channels.get('new_channel')
        assert isinstance(channel, Channel)
        channel_same = self.ably.channels.get('new_channel')
        assert channel is channel_same

    def test_channels_get_returns_new_with_options(self):
        key = generate_random_key()
        channel = self.ably.channels.get('new_channel', cipher={'key': key})
        assert isinstance(channel, Channel)
        assert channel.cipher.secret_key is key

    def test_channels_get_updates_existing_with_options(self):
        key = generate_random_key()
        channel = self.ably.channels.get('new_channel', cipher={'key': key})
        assert channel.cipher is not None

        channel_same = self.ably.channels.get('new_channel', cipher=None)
        assert channel is channel_same
        assert channel.cipher is None

    def test_channels_get_doesnt_updates_existing_with_none_options(self):
        key = generate_random_key()
        channel = self.ably.channels.get('new_channel', cipher={'key': key})
        assert channel.cipher is not None

        channel_same = self.ably.channels.get('new_channel')
        assert channel is channel_same
        assert channel.cipher is not None

    def test_channels_in(self):
        assert 'new_channel' not in self.ably.channels
        self.ably.channels.get('new_channel')
        new_channel_2 = self.ably.channels.get('new_channel_2')
        assert 'new_channel' in self.ably.channels
        assert new_channel_2 in self.ably.channels

    def test_channels_iteration(self):
        channel_names = ['channel_{}'.format(i) for i in range(5)]
        [self.ably.channels.get(name) for name in channel_names]

        assert isinstance(self.ably.channels, Iterable)
        for name, channel in zip(channel_names, self.ably.channels):
            assert isinstance(channel, Channel)
            assert name == channel.name

    def test_channels_release(self):
        self.ably.channels.get('new_channel')
        self.ably.channels.release('new_channel')

        with pytest.raises(KeyError):
            self.ably.channels.release('new_channel')

    def test_channels_del(self):
        self.ably.channels.get('new_channel')
        del self.ably.channels['new_channel']

        with pytest.raises(KeyError):
            del self.ably.channels['new_channel']

    def test_channel_has_presence(self):
        channel = self.ably.channels.get('new_channnel')
        assert channel.presence
        assert isinstance(channel.presence, Presence)

    def test_without_permissions(self):
        key = test_vars["keys"][2]
        ably = RestSetup.get_ably_rest(key=key["key_str"])
        with pytest.raises(AblyException) as excinfo:
            ably.channels['test_publish_without_permission'].publish('foo', 'woop')

        assert 'not permitted' in excinfo.value.message
