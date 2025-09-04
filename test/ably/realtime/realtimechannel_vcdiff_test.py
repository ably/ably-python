import asyncio
import json

from ably import VCDiffPlugin
from ably.realtime.realtime_channel import ChannelOptions
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase, WaitableEvent
from ably.realtime.connection import ConnectionState
from ably.types.options import VCDiffDecoder


class MockVCDiffDecoder(VCDiffDecoder):
    """Test VCDiff decoder that tracks number of calls"""

    def __init__(self):
        self.number_of_calls = 0
        self.last_decoded_data = None
        self.plugin = VCDiffPlugin()

    def decode(self, delta: bytes, base: bytes) -> bytes:
        self.number_of_calls += 1
        self.last_decoded_data = self.plugin.decode(delta, base)
        return self.last_decoded_data


class FailingVCDiffDecoder(VCDiffDecoder):
    """VCDiff decoder that always fails"""

    def decode(self, delta: bytes, base: bytes) -> bytes:
        raise Exception("Failed to decode delta.")


class TestRealtimeChannelVCDiff(BaseAsyncTestCase):
    async def asyncSetUp(self):
        self.test_vars = await TestApp.get_test_vars()
        self.valid_key_format = "api:key"

        # Test data equivalent to JavaScript version
        self.test_data = [
            {'foo': 'bar', 'count': 1, 'status': 'active'},
            {'foo': 'bar', 'count': 2, 'status': 'active'},
            {'foo': 'bar', 'count': 2, 'status': 'inactive'},
            {'foo': 'bar', 'count': 3, 'status': 'inactive'},
            {'foo': 'bar', 'count': 3, 'status': 'active'},
        ]

    def _equals(self, a, b):
        """Helper method to compare objects like the JavaScript version"""
        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    async def test_delta_plugin(self):
        """Test VCDiff delta plugin functionality"""
        test_vcdiff_decoder = MockVCDiffDecoder()
        ably = await TestApp.get_ably_realtime(vcdiff_decoder=test_vcdiff_decoder)

        try:
            await asyncio.wait_for(ably.connection.once_async(ConnectionState.CONNECTED), timeout=5)

            channel = ably.channels.get('delta_plugin', ChannelOptions(params={'delta': 'vcdiff'}))
            await channel.attach()

            messages_received = []
            waitable_event = WaitableEvent()

            def on_message(message):
                try:
                    index = int(message.name)
                    messages_received.append(message.data)

                    if index == len(self.test_data) - 1:
                        # All messages received
                        waitable_event.finish()
                except Exception as e:
                    waitable_event.finish()
                    raise e

            await channel.subscribe(on_message)

            # Publish all test messages
            for i, data in enumerate(self.test_data):
                await channel.publish(str(i), data)

            # Wait for all messages to be received
            await waitable_event.wait(timeout=30)
            for (expected_message, actual_message) in zip(self.test_data, messages_received):
                assert expected_message == actual_message, f"Check message.data for message {expected_message}"

            assert test_vcdiff_decoder.number_of_calls == len(self.test_data) - 1, "Check number of delta messages"

        finally:
            await ably.close()

    async def test_unused_plugin(self):
        """Test that VCDiff plugin is not used when delta is not enabled"""
        test_vcdiff_decoder = MockVCDiffDecoder()
        ably = await TestApp.get_ably_realtime(vcdiff_decoder=test_vcdiff_decoder)

        try:
            await asyncio.wait_for(ably.connection.once_async(ConnectionState.CONNECTED), timeout=5)

            # Channel without delta parameter
            channel = ably.channels.get('unused_plugin')
            await channel.attach()

            messages_received = []
            waitable_event = WaitableEvent()

            def on_message(message):
                try:
                    index = int(message.name)
                    messages_received.append(message.data)

                    if index == len(self.test_data) - 1:
                        waitable_event.finish()
                except Exception as e:
                    waitable_event.finish()
                    raise e

            await channel.subscribe(on_message)

            # Publish all test messages
            for i, data in enumerate(self.test_data):
                await channel.publish(str(i), data)

            # Wait for all messages to be received
            await waitable_event.wait(timeout=30)
            assert test_vcdiff_decoder.number_of_calls == 0, "Check number of delta messages"
            for (expected_message, actual_message) in zip(self.test_data, messages_received):
                assert expected_message == actual_message, f"Check message.data for message {expected_message}"
        finally:
            await ably.close()

    async def test_delta_decode_failure_recovery(self):
        """Test channel recovery when VCDiff decode fails"""
        failing_decoder = FailingVCDiffDecoder()
        ably = await TestApp.get_ably_realtime(vcdiff_decoder=failing_decoder)

        try:
            await asyncio.wait_for(ably.connection.once_async(ConnectionState.CONNECTED), timeout=5)

            channel = ably.channels.get('decode_failure_recovery', ChannelOptions(params={'delta': 'vcdiff'}))

            # Monitor for attaching state changes
            attaching_events = []

            def on_attaching(state_change):
                attaching_events.append(state_change)
                # RTL18c - Check error code
                if state_change.reason and state_change.reason.code:
                    assert state_change.reason.code == 40018, "Check error code passed through per RTL18c"

            channel.on('attaching', on_attaching)
            await channel.attach()

            messages_received = []
            waitable_event = WaitableEvent()

            def on_message(message):
                try:
                    index = int(message.name)
                    messages_received.append(message.data)

                    if index == len(self.test_data) - 1:
                        waitable_event.finish()
                except Exception as e:
                    waitable_event.finish()
                    raise e

            await channel.subscribe(on_message)

            # Publish all test messages
            for i, data in enumerate(self.test_data):
                await channel.publish(str(i), data)

            # Wait for messages - should recover and receive them
            await waitable_event.wait(timeout=30)

            # Should have triggered at least one reattach due to decode failure
            assert len(attaching_events) > 0, "Should have triggered channel reattaching"

            for (expected_message, actual_message) in zip(self.test_data, messages_received):
                assert expected_message == actual_message, f"Check message.data for message {expected_message}"
        finally:
            await ably.close()
