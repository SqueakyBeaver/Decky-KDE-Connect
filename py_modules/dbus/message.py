from enum import Enum
from typing import Any


class MessageType(Enum):
    INVALID = 0x0
    METHOD_CALL = 0x1
    METHOD_RETURN = 0x2
    ERROR = 0x3
    SIGNAL = 0x4


class MessageFlag(Enum):
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


class Message:
    def __init__(
        self,
        type: MessageType,
        bus_name: str,
        obj_path: str,
        interface: str,
        member: str,
        *args: Any,
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
        self._message_type = type
        self._obj_path = obj_path
        self._interface = interface
        self._member = member
        self._bus_name = bus_name
        self._args = [*args]
        self._serial = 17
        # The signature of the header is:
        # "yyyyuua(yv)"
        # Written out more readably, this is:
        # BYTE, BYTE, BYTE, BYTE, UINT32, UINT32, ARRAY of STRUCT of (BYTE,VARIANT)

    def get_bytes(self):
        """
        Get the byte representation of this message that is ready to be sent
        """
        pass

    def _marshal(self):
        """
        Marshall the message
        """
        body = []
        header_fields = [
            (HeaderField.PATH, self._obj_path),
            (HeaderField.INTERFACE, self._interface),
            (HeaderField.MEMBER, self._member),
            (HeaderField.DESTINATION, self._bus_name),
            (HeaderField.SIGNATURE, "todo"),
        ]
        header = [
            "B",  # big endian
            self._message_type.value,
            0,
            1,
            len(body),
            self._serial,
            header_fields,
        ]

        return
