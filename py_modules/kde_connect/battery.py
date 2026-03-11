"""
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.kde.kdeconnect.device.battery">
    <property name="charge" type="i" access="read"/>
    <property name="isCharging" type="b" access="read"/>
    <signal name="refreshed">
      <arg name="isCharging" type="b" direction="out"/>
      <arg name="charge" type="i" direction="out"/>
    </signal>
  </interface>
</node>
"""

from dbus import DBusInterface


class BatteryInterface(DBusInterface):
    def __init__(self, device_id: str):
        super().__init__(name="org.kde.kdeconnect.device.battery")
        self.device_id = device_id

    @property
    def charge(self):
        return self._get(self.device_id, "charge")


b = BatteryInterface("9fb8a57bfe364db18670ec0460d0f711")

print(b.charge)

