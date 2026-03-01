import asyncio
import os
from io import BufferedRWPair
from socket import AF_UNIX, SOCK_STREAM, socket
from typing import Callable


class DBusInterface:
    """
    A DBus Interface tailored to the KDEConnect bus
    """

    def __init__(self):
        self._bus_name = "org.kde.kdeconnect"
        self._session_bus_path = f"/run/user/{os.getuid()}/bus"

        self._sock: socket | None
        self._stream: BufferedRWPair
        self._fd: int

        self._loop = asyncio.get_event_loop()

        self._connect()

    def _get_object_path(self, device_id: str, interface: str):
        """
        Get an object path from a device name and an interface

        :param device_id: The device id given by KDEConnect (i.e. "9fb8a57bfe364db18670ec0460d0f711")
        :param interface: The interface which you want to find the object path for (i.e. "org.kde.kdeconnect.device.battery")
        """
        module = interface.removeprefix("org.kde.kdeconnect.device")
        if module:
            module = module.replace(".", "/")

        return f"/modules/kdeconnect/devices/{device_id}{module}"

    def _connect(self):
        """
        Connect to the session bus
        """
        self._sock = socket(AF_UNIX, SOCK_STREAM)
        self._stream = self._sock.makefile("rwb")
        self._fd = self._sock.fileno()

        self._sock.connect(self._session_bus_path)
        self._sock.setblocking(False)

    def get(self, device_id: str, interface: str, property: str):
        """
        Get a property of a given interface

        :param device_id: The id of the device that is given by KDEConnect (i.e. "9fb8a57bfe364db18670ec0460d0f711")
        :param interface: The name of the interface (i.e. "org.kde.kdeconnect.device.battery")
        :param property: The name of the propert (i.e. "charge")
        """
        obj_path = self._get_object_path(device_id, interface)

    def subscribe(self, interface: str, signal: str, callback: Callable):
        """
        Subscribe to a signal on a given interface

        :param interface: Name of the interface (i.e. "org.kde.kdeconnect.device.battery")
        :param signal: Name of the signal (i.e. "refreshed")
        :param callback: A callback that will be run when the signal is emitted
        """
