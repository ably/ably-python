import logging
from enum import IntEnum

from ably.types.mixins import EncodeDataMixin
from ably.util.encoding import encode_data
from ably.util.helper import to_text

log = logging.getLogger(__name__)


class AnnotationAction(IntEnum):
    """Annotation action types"""
    ANNOTATION_CREATE = 0
    ANNOTATION_DELETE = 1


class Annotation(EncodeDataMixin):
    """
    Represents an annotation on a message, such as a reaction or other metadata.

    Annotations are not encrypted as they need to be parsed by the server for summarization.
    """

    def __init__(self,
                 action=None,
                 serial=None,
                 message_serial=None,
                 type=None,
                 name=None,
                 count=None,
                 data=None,
                 encoding='',
                 client_id=None,
                 timestamp=None,
                 extras=None):
        """
        Args:
            action: The action type - either 'annotation.create' or 'annotation.delete'
            serial: A unique identifier for the annotation
            message_serial: The serial of the message this annotation is for
            type: The type of annotation (e.g., 'reaction', 'like', etc.)
            name: The name/value of the annotation (e.g., specific emoji)
            count: Count associated with the annotation
            data: Optional data payload for the annotation
            encoding: Encoding format for the data
            client_id: The client ID that created this annotation
            timestamp: Timestamp of the annotation
            extras: Additional metadata
        """
        super().__init__(encoding)

        self.__serial = to_text(serial) if serial is not None else None
        self.__message_serial = to_text(message_serial) if message_serial is not None else None
        self.__type = to_text(type) if type is not None else None
        self.__name = to_text(name) if name is not None else None
        self.__action = action if action is not None else AnnotationAction.ANNOTATION_CREATE
        self.__count = count
        self.__data = data
        self.__client_id = to_text(client_id) if client_id is not None else None
        self.__timestamp = timestamp
        self.__extras = extras

    def __eq__(self, other):
        if isinstance(other, Annotation):
            return (self.serial == other.serial
                    and self.message_serial == other.message_serial
                    and self.type == other.type
                    and self.name == other.name
                    and self.action == other.action)
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Annotation):
            result = self.__eq__(other)
            if result != NotImplemented:
                return not result
        return NotImplemented

    @property
    def action(self):
        return self.__action

    @property
    def serial(self):
        return self.__serial

    @property
    def message_serial(self):
        return self.__message_serial

    @property
    def type(self):
        return self.__type

    @property
    def name(self):
        return self.__name

    @property
    def count(self):
        return self.__count

    @property
    def data(self):
        return self.__data

    @property
    def client_id(self):
        return self.__client_id

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def extras(self):
        return self.__extras

    def as_dict(self, binary=False):
        """
        Convert annotation to dictionary format for API communication.

        Note: Annotations are not encrypted as they need to be parsed by the server.
        """
        request_body = {
            'action': int(self.action) if self.action is not None else None,
            'serial': self.serial,
            'messageSerial': self.message_serial,
            'type': self.type,  # Annotation type (not data type)
            'name': self.name,
            'count': self.count,
            'clientId': self.client_id or None,
            'timestamp': self.timestamp or None,
            'extras': self.extras,
            **encode_data(self.data, self._encoding_array, binary)
        }

        # None values aren't included
        request_body = {k: v for k, v in request_body.items() if v is not None}

        return request_body

    @staticmethod
    def from_encoded(obj, cipher=None, context=None):
        """
        Create an Annotation from an encoded object received from the API.

        Note: cipher parameter is accepted for consistency but annotations are not encrypted.
        """
        action = obj.get('action')
        serial = obj.get('serial')
        message_serial = obj.get('messageSerial')
        type_val = obj.get('type')
        name = obj.get('name')
        count = obj.get('count')
        data = obj.get('data')
        encoding = obj.get('encoding', '')
        client_id = obj.get('clientId')
        timestamp = obj.get('timestamp')
        extras = obj.get('extras', None)

        # Decode data if present
        decoded_data = Annotation.decode(data, encoding, cipher, context) if data is not None else {}

        # Convert action from int to enum
        if action is not None:
            try:
                action = AnnotationAction(action)
            except ValueError:
                # If it's not a valid action value, store as None
                action = None
        else:
            action = None

        return Annotation(
            action=action,
            serial=serial,
            message_serial=message_serial,
            type=type_val,
            name=name,
            count=count,
            client_id=client_id,
            timestamp=timestamp,
            extras=extras,
            **decoded_data
        )

    @staticmethod
    def from_encoded_array(obj_array, cipher=None, context=None):
        """Create an array of Annotations from encoded objects"""
        return [Annotation.from_encoded(obj, cipher, context) for obj in obj_array]

    @staticmethod
    def from_values(values):
        """Create an Annotation from a dict of values"""
        return Annotation(**values)

    def __str__(self):
        return (
            f"Annotation(action={self.action}, messageSerial={self.message_serial}, "
            f"type={self.type}, name={self.name})"
        )

    def __repr__(self):
        return self.__str__()


def make_annotation_response_handler(cipher=None):
    """Create a response handler for annotation API responses"""
    def annotation_response_handler(response):
        annotations = response.to_native()
        return Annotation.from_encoded_array(annotations, cipher=cipher)
    return annotation_response_handler


def make_single_annotation_response_handler(cipher=None):
    """Create a response handler for single annotation API responses"""
    def single_annotation_response_handler(response):
        annotation = response.to_native()
        return Annotation.from_encoded(annotation, cipher=cipher)
    return single_annotation_response_handler
