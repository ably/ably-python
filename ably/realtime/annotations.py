from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ably.rest.annotations import RestAnnotations, construct_validate_annotation
from ably.transport.websockettransport import ProtocolMessageAction
from ably.types.annotation import AnnotationAction
from ably.types.channelstate import ChannelState
from ably.types.flags import Flag
from ably.util.eventemitter import EventEmitter
from ably.util.exceptions import AblyException
from ably.util.helper import is_callable_or_coroutine

if TYPE_CHECKING:
    from ably.realtime.channel import RealtimeChannel
    from ably.realtime.connectionmanager import ConnectionManager

log = logging.getLogger(__name__)


class RealtimeAnnotations:
    """
    Provides realtime methods for managing annotations on messages,
    including publishing annotations and subscribing to annotation events.
    """

    __connection_manager: ConnectionManager
    __channel: RealtimeChannel

    def __init__(self, channel: RealtimeChannel, connection_manager: ConnectionManager):
        """
        Initialize RealtimeAnnotations.

        Args:
            channel: The Realtime Channel this annotations instance belongs to
        """
        self.__channel = channel
        self.__connection_manager = connection_manager
        self.__subscriptions = EventEmitter()
        self.__rest_annotations = RestAnnotations(channel)

    async def publish(self, msg_or_serial, annotation: dict, params: dict | None = None):
        """
        Publish an annotation on a message via the realtime connection.

        Args:
            msg_or_serial: Either a message serial (string) or a Message object
            annotation: Dict containing annotation properties (type, name, data, etc.)
            params: Optional dict of query parameters

        Returns:
            None

        Raises:
            AblyException: If the request fails, inputs are invalid, or channel is in unpublishable state
        """
        annotation = construct_validate_annotation(msg_or_serial, annotation)

        # Check if channel and connection are in publishable state
        self.__channel._throw_if_unpublishable_state()

        log.info(
            f'RealtimeAnnotations.publish(), channelName = {self.__channel.name}, '
            f'sending annotation with messageSerial = {annotation.message_serial}, '
            f'type = {annotation.type}'
        )

        # Convert to wire format (array of annotations)
        wire_annotation = annotation.as_dict(binary=self.__channel.ably.options.use_binary_protocol)

        # Build protocol message
        protocol_message = {
            "action": ProtocolMessageAction.ANNOTATION,
            "channel": self.__channel.name,
            "annotations": [wire_annotation],
        }

        if params:
            # Stringify boolean params
            stringified_params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
            protocol_message["params"] = stringified_params

        # Send via WebSocket
        await self.__connection_manager.send_protocol_message(protocol_message)

    async def delete(
        self,
        msg_or_serial,
        annotation: dict,
        params: dict | None = None,
    ):
        """
        Delete an annotation on a message.

        This is a convenience method that sets the action to 'annotation.delete'
        and calls publish().

        Args:
            msg_or_serial: Either a message serial (string) or a Message object
            annotation: Dict containing annotation properties
            params: Optional dict of query parameters

        Returns:
            None

        Raises:
            AblyException: If the request fails or inputs are invalid
        """
        annotation_values = annotation.copy()
        annotation_values['action'] = AnnotationAction.ANNOTATION_DELETE
        return await self.publish(msg_or_serial, annotation_values, params)

    async def subscribe(self, *args):
        """
        Subscribe to annotation events on this channel.

        Parameters
        ----------
        *args: type, listener
            Subscribe type and listener

            arg1(type): str, optional
                Subscribe to annotations of the given type

            arg2(listener): callable
                Subscribe to all annotations on the channel

            When no type is provided, arg1 is used as the listener.

        Raises
        ------
        AblyException
            If unable to subscribe due to invalid channel state or missing ANNOTATION_SUBSCRIBE mode
        ValueError
            If no valid subscribe arguments are passed
        """
        # Parse arguments similar to channel.subscribe
        if len(args) == 0:
            raise ValueError("annotations.subscribe called without arguments")

        if len(args) >= 2 and isinstance(args[0], str):
            annotation_type = args[0]
            if not args[1]:
                raise ValueError("annotations.subscribe called without listener")
            if not is_callable_or_coroutine(args[1]):
                raise ValueError("subscribe listener must be function or coroutine function")
            listener = args[1]
        elif is_callable_or_coroutine(args[0]):
            listener = args[0]
            annotation_type = None
        else:
            raise ValueError('invalid subscribe arguments')

        # Register subscription
        if annotation_type is not None:
            self.__subscriptions.on(annotation_type, listener)
        else:
            self.__subscriptions.on(listener)

        await self.__channel.attach()

        # Check if ANNOTATION_SUBSCRIBE mode is enabled
        if self.__channel.state == ChannelState.ATTACHED:
            if Flag.ANNOTATION_SUBSCRIBE not in self.__channel.modes:
                raise AblyException(
                    message="You are trying to add an annotation listener, but you haven't requested the "
                    "annotation_subscribe channel mode in ChannelOptions, so this won't do anything "
                    "(we only deliver annotations to clients who have explicitly requested them)",
                    code=93001,
                    status_code=400,
                )

    def unsubscribe(self, *args):
        """
        Unsubscribe from annotation events on this channel.

        Parameters
        ----------
        *args: type, listener
            Unsubscribe type and listener

            arg1(type): str, optional
                Unsubscribe from annotations of the given type

            arg2(listener): callable
                Unsubscribe from all annotations on the channel

            When no type is provided, arg1 is used as the listener.

        Raises
        ------
        ValueError
            If no valid unsubscribe arguments are passed
        """
        if len(args) == 0:
            raise ValueError("annotations.unsubscribe called without arguments")

        if len(args) >= 2 and isinstance(args[0], str):
            annotation_type = args[0]
            listener = args[1]
            self.__subscriptions.off(annotation_type, listener)
        elif is_callable_or_coroutine(args[0]):
            listener = args[0]
            self.__subscriptions.off(listener)
        else:
            raise ValueError('invalid unsubscribe arguments')

    def _process_incoming(self, incoming_annotations):
        """
        Process incoming annotations from the server.

        This is called internally when ANNOTATION protocol messages are received.

        Args:
            incoming_annotations: List of Annotation objects received from the server
        """
        for annotation in incoming_annotations:
            # Emit to type-specific listeners and catch-all listeners
            annotation_type = annotation.type or ''
            self.__subscriptions._emit(annotation_type, annotation)

    async def get(self, msg_or_serial, params: dict | None = None):
        """
        Retrieve annotations for a message with pagination support.

        This delegates to the REST implementation.

        Args:
            msg_or_serial: Either a message serial (string) or a Message object
            params: Optional dict of query parameters (limit, start, end, direction)

        Returns:
            PaginatedResult: A paginated result containing Annotation objects

        Raises:
            AblyException: If the request fails or serial is invalid
        """
        # Delegate to REST implementation
        return await self.__rest_annotations.get(msg_or_serial, params)
