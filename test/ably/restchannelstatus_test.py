import logging

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, BaseAsyncTestCase

log = logging.getLogger(__name__)


class TestRestChannelStatus(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    async def setUp(self):
        self.ably = await RestSetup.get_ably_rest()

    async def tearDown(self):
        await self.ably.close()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    async def test_channel_status(self):
        channel_name = self.get_channel_name('test_channel_status')
        channel = self.ably.channels[channel_name]

        channel_status = await channel.status()

        assert channel_status is not None, "Expected non-None channel_status"
        assert channel_name == channel_status.channel_id, "Expected channel name to match"
        assert channel_status.status.is_active is True, "Expected is_active to be True"
