import asyncio
import logging

import pytest

from ably import AblyException
from ably.types.annotation import AnnotationAction
from ably.types.channeloptions import ChannelOptions
from ably.types.message import MessageAction
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase, assert_waiter
from ably.types.channelmode import ChannelMode

log = logging.getLogger(__name__)


@pytest.mark.parametrize("transport", ["json", "msgpack"], ids=["JSON", "MsgPack"])
class TestRealtimeAnnotations(BaseAsyncTestCase):

    @pytest.fixture(autouse=True)
    async def setup(self, transport):
        self.test_vars = await TestApp.get_test_vars()
        self.ably = await TestApp.get_ably_realtime(
            use_binary_protocol=True if transport == 'msgpack' else False,
        )
        self.rest = await TestApp.get_ably_rest(
            use_binary_protocol=True if transport == 'msgpack' else False,
        )

    async def test_publish_and_subscribe_annotations(self):
        """Test publishing and subscribing to annotations (matches JS test)"""
        channel_options = ChannelOptions(modes=[
            ChannelMode.PUBLISH,
            ChannelMode.SUBSCRIBE,
            ChannelMode.ANNOTATION_PUBLISH,
            ChannelMode.ANNOTATION_SUBSCRIBE
        ])
        channel = self.ably.channels.get(
            self.get_channel_name('mutable:publish_subscribe_annotation'),
            channel_options
        )
        rest_channel = self.rest.channels[channel.name]
        await channel.attach()

        # Setup annotation listener
        annotation_future = asyncio.Future()

        async def on_annotation(annotation):
            if not annotation_future.done():
                annotation_future.set_result(annotation)

        await channel.annotations.subscribe(on_annotation)

        # Publish a message
        publish_result = await channel.publish('message', 'foobar')

        # Reset for next message (summary)
        message_summary = asyncio.Future()

        def on_message(msg):
            if not message_summary.done():
                message_summary.set_result(msg)

        await channel.subscribe('message', on_message)

        # Publish annotation using realtime
        await channel.annotations.publish(publish_result.serials[0], {
            'type': 'reaction:multiple.v1',
            'name': '👍'
        })

        # Wait for annotation
        annotation = await annotation_future
        assert annotation.action == AnnotationAction.ANNOTATION_CREATE
        assert annotation.message_serial == publish_result.serials[0]
        assert annotation.type == 'reaction:multiple.v1'
        assert annotation.name == '👍'
        assert annotation.serial > annotation.message_serial

        # Wait for summary message
        # summary = await message_summary
        # assert summary.action == MessageAction.META
        # assert summary.serial == publish_result.serials[0]
        #
        # # Try again but with REST publish
        # annotation_future2 = asyncio.Future()
        #
        # async def on_annotation2(annotation):
        #     if not annotation_future2.done():
        #         annotation_future2.set_result(annotation)
        #
        # await channel.annotations.subscribe(on_annotation2)
        #
        # await rest_channel.annotations.publish(publish_result.serials[0], {
        #     'type': 'reaction:multiple.v1',
        #     'name': '😕'
        # })
        #
        # annotation = await annotation_future2
        # assert annotation.action == AnnotationAction.ANNOTATION_CREATE
        # assert annotation.message_serial == publish_result.serials[0]
        # assert annotation.type == 'reaction:multiple.v1'
        # assert annotation.name == '😕'
        # assert annotation.serial > annotation.message_serial

    async def test_get_all_annotations_for_a_message(self):
        """Test retrieving all annotations with pagination (matches JS test)"""
        channel_options = ChannelOptions(params={
            'modes': 'publish,subscribe,annotation_publish,annotation_subscribe'
        })
        channel = self.ably.channels.get(
            self.get_channel_name('mutable:get_all_annotations_for_a_message'),
            channel_options
        )
        await channel.attach()

        # Setup message listener
        message_future = asyncio.Future()

        def on_message(msg):
            if not message_future.done():
                message_future.set_result(msg)

        await channel.subscribe('message', on_message)

        # Publish a message
        await channel.publish('message', 'foobar')
        message = await message_future

        # Publish multiple annotations
        emojis = ['👍', '😕', '👎', '👍👍', '😕😕', '👎👎']
        for emoji in emojis:
            await channel.annotations.publish(message.serial, {
                'type': 'reaction:multiple.v1',
                'name': emoji
            })

        # Wait for all annotations to appear
        annotations = []

        async def check_annotations():
            nonlocal annotations
            res = await channel.annotations.get(message.serial, {})
            annotations = res.items
            return len(annotations) == 6

        await assert_waiter(check_annotations, timeout=10)

        # Verify annotations
        assert annotations[0].action == AnnotationAction.ANNOTATION_CREATE
        assert annotations[0].message_serial == message.serial
        assert annotations[0].type == 'reaction:multiple.v1'
        assert annotations[0].name == '👍'
        assert annotations[1].name == '😕'
        assert annotations[2].name == '👎'
        assert annotations[1].serial > annotations[0].serial
        assert annotations[2].serial > annotations[1].serial

        # Test pagination
        res = await channel.annotations.get(message.serial, {'limit': 2})
        assert len(res.items) == 2
        assert [a.name for a in res.items] == ['👍', '😕']
        assert res.has_next()

        res = await res.next()
        assert res is not None
        assert len(res.items) == 2
        assert [a.name for a in res.items] == ['👎', '👍👍']
        assert res.has_next()

        res = await res.next()
        assert res is not None
        assert len(res.items) == 2
        assert [a.name for a in res.items] == ['😕😕', '👎👎']
        assert not res.has_next()

    async def test_subscribe_by_annotation_type(self):
        """Test subscribing to specific annotation types"""
        channel_options = ChannelOptions(params={
            'modes': 'publish,subscribe,annotation_publish,annotation_subscribe'
        })
        channel = self.ably.channels.get(
            self.get_channel_name('mutable:subscribe_by_type'),
            channel_options
        )
        await channel.attach()

        # Setup message listener
        message_future = asyncio.Future()

        def on_message(msg):
            if not message_future.done():
                message_future.set_result(msg)

        await channel.subscribe('message', on_message)

        # Subscribe to specific annotation type
        reaction_future = asyncio.Future()

        async def on_reaction(annotation):
            if not reaction_future.done():
                reaction_future.set_result(annotation)

        await channel.annotations.subscribe('reaction:multiple.v1', on_reaction)

        # Publish message and annotation
        await channel.publish('message', 'test')
        message = await message_future

        # Temporary anti-flake measure (matches JS test)
        await asyncio.sleep(1)

        await channel.annotations.publish(message.serial, {
            'type': 'reaction:multiple.v1',
            'name': '👍'
        })

        # Should receive the annotation
        annotation = await reaction_future
        assert annotation.type == 'reaction:multiple.v1'
        assert annotation.name == '👍'

    async def test_unsubscribe_annotations(self):
        """Test unsubscribing from annotations"""
        channel_options = ChannelOptions(params={
            'modes': 'publish,subscribe,annotation_publish,annotation_subscribe'
        })
        channel = self.ably.channels.get(
            self.get_channel_name('mutable:unsubscribe_annotations'),
            channel_options
        )
        await channel.attach()

        # Setup message listener
        message_future = asyncio.Future()

        def on_message(msg):
            if not message_future.done():
                message_future.set_result(msg)

        await channel.subscribe('message', on_message)

        annotations_received = []

        async def on_annotation(annotation):
            annotations_received.append(annotation)

        await channel.annotations.subscribe(on_annotation)

        # Publish message and first annotation
        await channel.publish('message', 'test')
        message = await message_future

        # Temporary anti-flake measure (matches JS test)
        await asyncio.sleep(1)

        await channel.annotations.publish(message.serial, {
            'type': 'reaction:multiple.v1',
            'name': '👍'
        })

        # Wait for first annotation
        assert len(annotations_received) == 1

        # Unsubscribe
        channel.annotations.unsubscribe(on_annotation)

        # Publish another annotation
        await channel.annotations.publish(message.serial, {
            'type': 'reaction:multiple.v1',
            'name': '😕'
        })

        # Wait and verify we didn't receive it
        assert len(annotations_received) == 1

    async def test_delete_annotation(self):
        """Test deleting annotations"""
        channel_options = ChannelOptions(params={
            'modes': 'publish,subscribe,annotation_publish,annotation_subscribe'
        })
        channel = self.ably.channels.get(
            self.get_channel_name('mutable:delete_annotation'),
            channel_options
        )
        await channel.attach()

        # Setup message listener
        message_future = asyncio.Future()

        def on_message(msg):
            if not message_future.done():
                message_future.set_result(msg)

        await channel.subscribe('message', on_message)

        annotations_received = []

        async def on_annotation(annotation):
            annotations_received.append(annotation)

        await channel.annotations.subscribe(on_annotation)

        # Publish message and annotation
        await channel.publish('message', 'test')
        message = await message_future

        # Temporary anti-flake measure (matches JS test)
        await asyncio.sleep(1)

        await channel.annotations.publish(message.serial, {
            'type': 'reaction:multiple.v1',
            'name': '👍'
        })

        # Wait for create annotation
        assert len(annotations_received) == 1
        assert annotations_received[0].action == AnnotationAction.ANNOTATION_CREATE

        # Delete the annotation
        await channel.annotations.delete(message.serial, {
            'type': 'reaction:multiple.v1',
            'name': '👍'
        })

        # Wait for delete annotation
        assert len(annotations_received) == 2
        assert annotations_received[1].action == AnnotationAction.ANNOTATION_DELETE

    async def test_subscribe_without_annotation_mode_fails(self):
        """Test that subscribing without annotation_subscribe mode raises an error"""
        # Create channel without annotation_subscribe mode
        channel_options = ChannelOptions(params={
            'modes': 'publish,subscribe'
        })
        channel = self.ably.channels.get(
            self.get_channel_name('mutable:no_annotation_mode'),
            channel_options
        )
        await channel.attach()

        async def on_annotation(annotation):
            pass

        # Should raise error about missing annotation_subscribe mode
        with pytest.raises(AblyException) as exc_info:
            await channel.annotations.subscribe(on_annotation)

        assert exc_info.value.status_code == 400
        assert 'annotation_subscribe' in str(exc_info.value).lower()
