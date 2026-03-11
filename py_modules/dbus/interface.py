import asyncio
import os
from io import BufferedRWPair
from socket import socket
from typing import Callable

from dbus.connection import get_connection
from dbus.message import Message, MessageType
from dbus.signatures import Int32, String, Struct


def dbus_method(func: Callable):
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)

    return wrapper


# mpris_remote
# <method name="seek">
#   <arg name="offset" type="i" direction="in"/>
# </method>


def seek(offset: Int32):
    pass
    msg = Message(
        type=MessageType.METHOD_CALL,
        bus_name="org.kde.kdeconnect",
        obj_path="/modules/kdeconnect/devices/9fb8a57bfe364db18670ec0460d0f711/mprisremote",
        interface="org.kde.kdeconnect.device.mprisremote",
        member="seek",
        signature=[Int32()],
        data=[offset],
    )


class DBusInterface:
    """
    A DBus Interface tailored to the KDEConnect bus
    """

    def __init__(self, name: str):
        self._bus_name = "org.kde.kdeconnect"
        self._interface_name = name
        self._session_bus_path = f"/run/user/{os.getuid()}/bus"

        self._sock: socket | None
        self._stream: BufferedRWPair
        self._fd: int

        self._loop = asyncio.get_event_loop()

        self._conn = get_connection()

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

    def _get(self, device_id: str, property: str):
        """
        Get a property of a given interface

        :param device_id: The id of the device that is given by KDEConnect (i.e. "9fb8a57bfe364db18670ec0460d0f711")
        :param property: The name of the propert (i.e. "charge")
        """
        obj_path = self._get_object_path(device_id, self._interface_name)
        msg = Message(
            type=MessageType.METHOD_CALL,
            bus_name=self._bus_name,
            obj_path=obj_path,
            interface="org.freedesktop.DBus.Properties",
            member="Get",
            signature=[String(), String()],
            data=[self._interface_name, property],
        )
        
        res = self._conn.send(msg)
        return res

    def _get_all(self, device_id: str):
        obj_path = self._get_object_path(device_id, self._interface_name)
        msg = Message(
            type=MessageType.METHOD_CALL,
            bus_name=self._bus_name,
            obj_path=obj_path,
            interface="org.freedesktop.DBus.Properties",
            member="GetAll",
            signature=[String()],
            data=[self._interface_name],
        )

        res = self._conn.send(msg)
        return res



    def _subscribe(self, interface: str, signal: str, callback: Callable):
        """
        Subscribe to a signal on a given interface

        :param interface: Name of the interface (i.e. "org.kde.kdeconnect.device.battery")
        :param signal: Name of the signal (i.e. "refreshed")
        :param callback: A callback that will be run when the signal is emitted
        """
