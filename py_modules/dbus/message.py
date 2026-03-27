from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import Any

from dbus.signatures import (
    Byte,
    DBusType,
    Dictionary,
    ObjectPath,
    Signature,
    String,
    UInt32,
    Variant,
)


class MessageType(IntEnum):
    INVALID = 0x0
    METHOD_CALL = 0x1
    METHOD_RETURN = 0x2
    ERROR = 0x3
    SIGNAL = 0x4


class MessageFlag(IntFlag):
    NONE = 0x0
    NO_REPLY_EXPECTED = 0x1
    NO_AUTO_START = 0x2
    ALLOW_INTERACTIVE_AUTHORIZATION = 0x4


class HeaderField(IntEnum):
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
    endianness = ord("l")
    msg_type: MessageType
    flags: MessageFlag
    protocol = 1
    msg_length: int
    serial: int
    header_fields: dict[HeaderField, tuple[DBusType, Any]]

    buffer: bytearray = field(default_factory=bytearray)

    def align(self, n: int):
        offset = n - len(self.buffer) % n
        if offset == 0 or offset == n:
            return

        self.buffer += b"\0" * offset

    def marshall(self):
        self.buffer = bytearray(
            [
                self.endianness,
                self.msg_type.value,
                self.flags.value,
                self.protocol,
            ]
        )

        self.buffer += self.msg_length.to_bytes(4, "little") + self.serial.to_bytes(
            4, "little"
        )

        self.buffer += Dictionary(Byte(), Variant(), pad_arr_length=False).pack(
            self.header_fields
        )

        self.align(8)

    @classmethod
    def decode(cls, buf: bytes):
        """
        Decode a byte string into a message header

        :param buf: The bytes to decode
        :returns: The MessageHeader object and the bytes after the message header
        """
        """
        Example:
        l \x02 \x01 \x01 
        \x0b \x00 \x00 \x00 
        \x01 \x00 \x00 \x00
        
        Header Fields:
        Size: \x3d \x00 \x00 \x00 {
            \x06: \x01s\x00 \x06\x00\x00\x00 :1.396\x00
            \x00
            \x05: \x01u\x00 \x01\x00\x00\x00
            \x08: \x01g\x00 \x01s\x00
            \x00
            \x07: \x01s\x00 \x14\x00\x00\x00 org.freedesktop.DBus\x00
        }
        """

        endianness = buf[0]
        byteorder = "big" if endianness == b"B" else "little"

        msg_type = MessageType(buf[1])
        msg_flags = MessageFlag(buf[2])
        protocol_ver = buf[3]

        body_len = int.from_bytes(buf[4:8], byteorder)
        serial = buf[8:12]

        print(buf[12:])
        field_dict = Dictionary(Byte(), Variant(), byteorder=byteorder).decode(buf[12:])

        print(field_dict)


@dataclass
class MessageBody:
    signature: list[DBusType]
    sig_str: str = field(init=False)
    data: list[Any]

    buffer: bytearray = field(default_factory=bytearray)

    def __post_init__(self):
        self.sig_str = ""
        for i in self.signature:
            self.sig_str += i.to_dbus_str()

    def align(self, n: int):
        offset = n - len(self.buffer) % n
        if offset == 0 or offset == n:
            return

        self.buffer += b"\0" * offset

    def marshall(self):
        for sig, data in zip(self.signature, self.data):
            self.align(sig.align)
            self.buffer += sig.pack(data)


_serial = 1


class Message:
    header: MessageHeader
    body: MessageBody

    def __init__(
        self,
        *,
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
        global _serial

        self.message_type = type
        self.obj_path = obj_path
        self.interface = interface
        self.member = member
        self.bus_name = bus_name
        self.serial = _serial
        _serial += 1
        self.body = MessageBody(signature, data)

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
                HeaderField.PATH: (ObjectPath(), self.obj_path),
                HeaderField.INTERFACE: (String(), self.interface),
                HeaderField.MEMBER: (String(), self.member),
                HeaderField.DESTINATION: (String(), self.bus_name),
                HeaderField.SIGNATURE: (Signature(), self.body.sig_str),
            },
        )
        self.header.marshall()

        return self.header.buffer + self.body.buffer

    @classmethod
    def decode(cls, buf: bytes):
        """
        Decode one message from a given byte string

        :param buf: The bytes to parse
        :returns: The byte string after the message that was decoded
        """
        """
        Example:
        l \x02 \x01 \x01 
        \x0b \x00 \x00 \x00 
        \x01 \x00 \x00 \x00
        
        Header Fields:
        Size: \x3d \x00 \x00 \x00 {
            \x06: \x01s\x00 \x06\x00\x00\x00 :1.396\x00
            \x00
            \x05: \x01u\x00 \x01\x00\x00\x00
            \x08: \x01g\x00 \x01s\x00
            \x00
            \x07: \x01s\x00 \x14\x00\x00\x00 org.freedesktop.DBus\x00
        }
        Body:
        \x06\x00\x00\x00 :1.396\x00
        
        Signal:
        l \x04 \x01 \x01 
        \x0b\x00\x00\x00
        \x02\x00\x00\x00

        \x8d\x00\x00\x00 {
            \x01: \x01o\x00 \x15\x00\x00\x00 /org/freedesktop/DBus\x00
            \x00\x00
            \x02: \x01s\x00 \x14\x00\x00\x00 org.freedesktop.DBus\x00 
            \x00\x00\x00
            \x03: \x01s\x00 \x0c\x00\x00\x00 NameAcquired\x00
            \x00\x00\x00
            \x06: \x01s\x00 \x06\x00\x00\x00 :1.396\x00
            \x00
            \x08: \x01g\x00 \x01s\x00 
            \x00
            \x07: \x01s\x00 \x14\x00\x00\x00 org.freedesktop.DBus\x00
            \x00\x00\x00
        }
        \x06\x00\x00\x00 :1.396\x00'
        """
        header = MessageHeader.decode(buf)


if __name__ == "__main__":
    Message.decode(
        b"l\x02\x01\x01\x0b\x00\x00\x00\x01\x00\x00\x00\x3d\x00\x00\x00\x06\x01s\x00\x06\x00\x00\x00:1.396\x00\x00\x05\x01u\x00\x01\x00\x00\x00\x08\x01g\x00\x01s\x00\x00\x07\x01s\x00\x14\x00\x00\x00org.freedesktop.DBus\x00\x06\x00\x00\x00:1.396\x00"
    )
