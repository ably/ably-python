from __future__ import annotations

import json
import logging
from urllib import parse

import msgpack

from ably.http.paginatedresult import PaginatedResult, format_params
from ably.types.annotation import (
    Annotation,
    AnnotationAction,
    make_annotation_response_handler,
)
from ably.types.message import Message
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


def serial_from_msg_or_serial(msg_or_serial):
    """
    Extract the message serial from either a string serial or a Message object.

    Args:
        msg_or_serial: Either a string serial or a Message object with a serial property

    Returns:
        str: The message serial

    Raises:
        AblyException: If the input is invalid or serial is missing
    """
    if isinstance(msg_or_serial, str):
        message_serial = msg_or_serial
    elif isinstance(msg_or_serial, Message):
        message_serial = msg_or_serial.serial
    else:
        message_serial = None

    if not message_serial or not isinstance(message_serial, str):
        raise AblyException(
            message='First argument of annotations.publish() must be either a Message '
            '(or at least an object with a string `serial` property) or a message serial (string)',
            status_code=400,
            code=40003,
        )

    return message_serial


def construct_validate_annotation(msg_or_serial, annotation: dict):
    """
    Construct and validate an Annotation from input values.

    Args:
        msg_or_serial: Either a string serial or a Message object
        annotation: Dict of annotation properties or Annotation object

    Returns:
        Annotation: The constructed annotation

    Raises:
        AblyException: If the inputs are invalid
    """
    message_serial = serial_from_msg_or_serial(msg_or_serial)

    if not annotation or (not isinstance(annotation, dict) and not isinstance(annotation, Annotation)):
        raise AblyException(
            message='Second argument of annotations.publish() must be a dict or Annotation '
            '(the intended annotation to publish)',
            status_code=400,
            code=40003,
        )

    annotation_values = annotation.copy()
    annotation_values['message_serial'] = message_serial

    return Annotation.from_values(annotation_values)


class RestAnnotations:
    """
    Provides REST API methods for managing annotations on messages.
    """

    def __init__(self, channel):
        """
        Initialize RestAnnotations.

        Args:
            channel: The REST Channel this annotations instance belongs to
        """
        self.__channel = channel

    def __base_path_for_serial(self, serial):
        """
        Build the base API path for a message serial's annotations.

        Args:
            serial: The message serial

        Returns:
            str: The API path
        """
        channel_path = '/channels/{}/'.format(parse.quote_plus(self.__channel.name, safe=':'))
        return channel_path + 'messages/' + parse.quote_plus(serial, safe=':') + '/annotations'

    async def publish(
        self,
        msg_or_serial,
        annotation: dict | Annotation,
        params: dict | None = None,
    ):
        """
        Publish an annotation on a message.

        Args:
            msg_or_serial: Either a message serial (string) or a Message object
            annotation: Dict containing annotation properties (type, name, data, etc.) or Annotation object
            params: Optional dict of query parameters

        Returns:
            None

        Raises:
            AblyException: If the request fails or inputs are invalid
        """
        annotation = construct_validate_annotation(msg_or_serial, annotation)

        # Convert to wire format
        request_body = annotation.as_dict(binary=self.__channel.ably.options.use_binary_protocol)

        # Wrap in array as API expects array of annotations
        request_body = [request_body]

        # Encode based on protocol
        if not self.__channel.ably.options.use_binary_protocol:
            request_body = json.dumps(request_body, separators=(',', ':'))
        else:
            request_body = msgpack.packb(request_body, use_bin_type=True)

        # Build path
        path = self.__base_path_for_serial(annotation.message_serial)
        if params:
            params = {k: str(v).lower() if type(v) is bool else v for k, v in params.items()}
            path += '?' + parse.urlencode(params)

        # Send request
        await self.__channel.ably.http.post(path, body=request_body)

    async def delete(
        self,
        msg_or_serial,
        annotation: dict | Annotation,
        params: dict | None = None,
    ):
        """
        Delete an annotation on a message.

        This is a convenience method that sets the action to 'annotation.delete'
        and calls publish().

        Args:
            msg_or_serial: Either a message serial (string) or a Message object
            annotation: Dict containing annotation properties or Annotation object
            params: Optional dict of query parameters

        Returns:
            None

        Raises:
            AblyException: If the request fails or inputs are invalid
        """
        # Set action to delete
        if isinstance(annotation, Annotation):
            annotation_values = annotation.as_dict()
        else:
            annotation_values = annotation.copy()
        annotation_values['action'] = AnnotationAction.ANNOTATION_DELETE
        return await self.publish(msg_or_serial, annotation_values, params)

    async def get(self, msg_or_serial, params: dict | None = None):
        """
        Retrieve annotations for a message with pagination support.

        Args:
            msg_or_serial: Either a message serial (string) or a Message object
            params: Optional dict of query parameters (limit, start, end, direction)

        Returns:
            PaginatedResult: A paginated result containing Annotation objects

        Raises:
            AblyException: If the request fails or serial is invalid
        """
        message_serial = serial_from_msg_or_serial(msg_or_serial)

        # Build path
        params_str = format_params({}, **params) if params else ''
        path = self.__base_path_for_serial(message_serial) + params_str

        # Create annotation response handler
        annotation_handler = make_annotation_response_handler(cipher=None)

        # Return paginated result
        return await PaginatedResult.paginated_query(
            self.__channel.ably.http,
            url=path,
            response_processor=annotation_handler
        )
