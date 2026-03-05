from dataclasses import dataclass, field
from enum import Enum, Flag, IntEnum
from typing import Any

from dbus.signatures import DBusType, ObjectPath, Signature, String, UInt32, Variant


class MessageType(IntEnum):
    INVALID = 0x0
    METHOD_CALL = 0x1
    METHOD_RETURN = 0x2
    ERROR = 0x3
    SIGNAL = 0x4


class MessageFlag(Flag):
    NONE = 0x0
    NO_REPLY_EXPECTED = 0x1
    NO_AUTO_START = 0x2
    ALLOW_INTERACTIVE_AUTHORIZATION = 0x4


class HeaderField(Enum):
    INVALID = 0
    PATH = 1
    INTERFACE = 2
    MEMBER = 3
    ERROR_NAME = 4
    REPLY_SERIAL = 5
    DESTINATION = 6
    SENDER = 7
    SIGNATURE = 8
    UNIX_FDS = 9


HEADER_FIELD_TYPES = {
    HeaderField.PATH: Variant(ObjectPath()),
    HeaderField.INTERFACE: Variant(String()),
    HeaderField.MEMBER: Variant(String()),
    HeaderField.ERROR_NAME: Variant(String()),
    HeaderField.REPLY_SERIAL: Variant(UInt32()),
    HeaderField.DESTINATION: Variant(String()),
    HeaderField.SENDER: Variant(String()),
    HeaderField.SIGNATURE: Variant(Signature()),
    HeaderField.UNIX_FDS: Variant(UInt32()),
}


@dataclass
class MessageHeader:
    endianness = ord("B")
    msg_type: MessageType
    flags: MessageFlag
    protocol = 1
    msg_length: int
    serial: int
    header_fields: dict[HeaderField, Any]

    buffer = bytearray()

    def align(self, n: int):
        self.buffer += b"\0" * (n - len(self.buffer) % n)

    def marshall(self):
        self.buffer = bytearray(
            [
                self.endianness,
                self.msg_type.value,
                self.flags.value,
                self.protocol,
                self.msg_length,
                self.serial,
            ]
        )

        for header_field, data in self.header_fields.items():
            self.buffer += header_field.value.to_bytes()
            self.buffer += HEADER_FIELD_TYPES[header_field].pack(data)

        self.align(8)


@dataclass
class MessageBody:
    signature: list[DBusType]
    sig_str: str = field(init=False)
    data: list[Any]

    buffer = bytearray()

    def __post_init__(self):
        for i in self.signature:
            self.sig_str += i.to_dbus_str()

    def align(self, n: int):
        self.buffer += b"\0" * (n - len(self.buffer) % n)

    def marshall(self):
        for sig, data in zip(self.signature, self.data):
            self.align(sig.align)
            self.buffer += sig.pack(data)


class Message:
    def __init__(
        self,
        type: MessageType,
        bus_name: str,
        obj_path: str,
        interface: str,
        member: str,
        signature: list[DBusType],
        data: list[Any],
    ):
        """
        Create a new Message to send on the bus

        :param type: The message type
        :param bus_name: The name of the bus (i.e. "org.kde.kdeconnect")
        :param obj_path: The object path to send the message to
        :param interface: The interface to invoke a call on (i.e. "org.kde.kdeconnect.device.battery")
        :param member: The method name or signal name
        :param args: List of arguments that will make up the body of the message
        """
        self.message_type = type
        self.obj_path = obj_path
        self.interface = interface
        self.member = member
        self.bus_name = bus_name
        self.serial = 17
        self.body = MessageBody(signature, data)

        # The signature of the header is:
        # "yyyyuua(yv)"
        # Written out more readably, this is:
        # BYTE, BYTE, BYTE, BYTE, UINT32, UINT32, ARRAY of STRUCT of (BYTE,VARIANT)

    def get_bytes(self):
        """
        Get the byte representation of this message that is ready to be sent
        """
        return self._marshall()

    def _marshall(self):
        """
        Marshall the message
        """
        self.body.marshall()
        self.header = MessageHeader(
            self.message_type,
            MessageFlag.NONE,
            len(self.body.buffer),
            self.serial,
            {
                HeaderField.PATH: self.obj_path,
                HeaderField.INTERFACE: self.interface,
                HeaderField.MEMBER: self.member,
                HeaderField.DESTINATION: self.bus_name,
                HeaderField.SIGNATURE: self.body.sig_str,
            },
        )
        self.header.marshall()

        return self.header.buffer + self.body.buffer
