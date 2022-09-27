from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestRealtimeChannel(BaseAsyncTestCase):
    async def setUp(self):
        self.test_vars = await RestSetup.get_test_vars()
        self.valid_key_format = "api:key"

    async def test_channels_get(self):
        ably = await RestSetup.get_ably_realtime()
        channel = ably.channels.get('my_channel')
        assert channel == ably.channels.all['my_channel']
        await ably.close()

    async def test_channels_release(self):
        ably = await RestSetup.get_ably_realtime()
        ably.channels.get('my_channel')
        ably.channels.release('my_channel')
        assert ably.channels.all.get('my_channel') is None
        await ably.close()
