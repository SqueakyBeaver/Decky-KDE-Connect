import os
from socket import AF_UNIX, SOCK_STREAM, socket

from dbus.message import Message, MessageType


class DBusConnection:
    def __init__(self):
        self._bus_name = "org.kde.kdeconnect"
        self._session_bus_path = f"/run/user/{os.getuid()}/bus"

        self._sock = socket(AF_UNIX, SOCK_STREAM)
        self._sock.connect(self._session_bus_path)

        self._authenticate()

    def _authenticate(self):
        """Perform D-Bus authentication handshake"""
        self._sock.sendall(b"\0")

        uid_hex = str(os.getuid()).encode().hex().encode("ascii")
        auth_message = b"AUTH EXTERNAL " + uid_hex + "\r\n".encode("ascii")
        self._sock.sendall(auth_message)

        response = self._sock.recv(1024).decode("ascii")
        if not response.startswith("OK"):
            raise ConnectionError(f"D-Bus authentication failed: {response}")

        self._sock.sendall(b"BEGIN\r\n")
        self._hello()

    def _hello(self):
        msg = Message(
            type=MessageType.METHOD_CALL,
            bus_name="org.freedesktop.DBus",
            obj_path="/org/freedesktop/DBus",
            interface="org.freedesktop.DBus",
            member="Hello",
            signature=[],
            data=[],
        )

        res = self.send(msg)

    def send(self, msg: Message):
        """
        Simple send to bus

        :param msg: The message to send
        """
        b = msg.get_bytes()

        self._sock.sendall(b)

        return self._sock.recv(4096)


_connection: DBusConnection | None = None


def get_connection():
    global _connection

    if not _connection:
        _connection = DBusConnection()

    return _connection
