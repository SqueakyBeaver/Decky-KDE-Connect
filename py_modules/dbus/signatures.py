from abc import ABC, abstractmethod
from struct import Struct as CStruct
from typing import Any, override

from .utils import align_buf, marshall_str


class DBusType(ABC):
    dbus_code: str
    align: int

    @abstractmethod
    def is_valid(self, val: Any) -> bool:
        pass

    @abstractmethod
    def pack(self, data: Any) -> bytes:
        pass

    @abstractmethod
    def to_dbus_str(self) -> str:
        """
        Get the DBus signature string of this type
        """
        pass


class DBusBasicType(DBusType):
    _value: Any = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val: Any):
        if self.is_valid(val):
            self._value = val
        else:
            raise ValueError(f"{val} is not valid on class {self}")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} ({self.dbus_code})>"

    def to_dbus_str(self) -> str:
        """
        Get the DBus signature string of this type
        """
        return self.dbus_code


class DBusNumericType(DBusBasicType):
    struct_code: str
    _packer = CStruct("<B")

    def pack(self, data: int):
        return self._packer.pack(data)


class DBusStringType(DBusBasicType):
    def pack(self, data: str):
        """
        Turn string data into a set of bytes

        :param data: The string to pack
        """
        return marshall_str(data, self.align)


class DBusContainerType(DBusType):
    pass


class Invalid(DBusBasicType):
    dbus_code = "\0"
    align = 0


class Byte(DBusNumericType):
    dbus_code = "y"
    align = 1
    _value: int
    _packer = CStruct("<B")

    @override
    def is_valid(self, val: Any):
        return isinstance(val, int) and val.bit_length() <= 8


class Boolean(DBusNumericType):
    dbus_code = "b"
    align = 4
    _value: bool | int
    _packer = CStruct("<I")

    def is_valid(self, val: Any):
        return isinstance(val, int) and (val == 1 or val == 0)


class Int16(DBusNumericType):
    dbus_code = "n"
    align = 2
    _value: int
    _packer = CStruct("<h")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 16


class UInt16(DBusNumericType):
    dbus_code = "q"
    align = 2
    _value: int
    _packer = CStruct("<H")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 16 and val > 0


class Int32(DBusNumericType):
    dbus_code = "i"
    align = 4
    _value: int
    _packer = CStruct("<i")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 32


class UInt32(DBusNumericType):
    dbus_code = "u"
    align = 4
    _value: int
    _packer = CStruct("<I")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 32 and val > 0


class Int64(DBusNumericType):
    dbus_code = "x"
    align = 8
    _value: int
    _packer = CStruct("<q")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 64


class UInt64(DBusNumericType):
    dbus_code = "t"
    align = 8
    _value: int
    _packer = CStruct("<Q")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 64 and val > 0


class Double(DBusNumericType):
    dbus_code = "d"
    align = 8
    _value: float
    _packer = CStruct("<d")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, float) or isinstance(val, int)

    @override
    def pack(self, data: float) -> bytes:
        """
        Turn a given float into bytes

        :param data: The float to pack
        """
        return self._packer.pack(data)


class String(DBusStringType):
    dbus_code = "s"
    align = 4
    _value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


class ObjectPath(DBusStringType):
    dbus_code = "o"
    align = 4
    _value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


class Signature(DBusStringType):
    dbus_code = "g"
    align = 1
    _value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str) and len(val) < 256


class Array[T: DBusType](DBusContainerType, list):
    dbus_code = "a"
    align = 4
    align_elem: int

    def __init__(self, elem_type: T):
        self.elem_type = elem_type
        self.pack_elem = elem_type.pack
        self.align_elem = elem_type.align

    def pack(self, data: list[T]) -> bytes:
        buf = bytearray()

        for i in data:
            buf += self.pack_elem(i)

        return bytes(align_buf(len(buf).to_bytes(4, "little"), self.align_elem) + buf)

    def is_valid(self, val):
        return True

    def to_dbus_str(self) -> str:
        return f"a{self.elem_type.dbus_code}"

    def __repr__(self):
        return f"<Array [{self.elem_type}]>"


class Struct(DBusContainerType):
    dbus_code = "("
    end_dbus_code = ")"
    align = 8

    def __init__(self, *contents: DBusType):
        self.contents = contents
        self.packers = [c.pack for c in contents]
        self.child_align = tuple([i.align for i in contents])  # type: ignore

    def is_valid(self, val: Any) -> bool:
        # TODO: Check type (I'm lazy)
        return True

    def pack(self, data: tuple[Any, ...]) -> bytes:
        buf = bytearray()

        for pack, i in zip(self.packers, data):
            buf += pack(i)

        return bytes(buf)

    def to_dbus_str(self) -> str:
        return f"({''.join([c.dbus_code for c in self.contents])})"  # type: ignore

    def __repr__(self):
        return f"<Struct({','.join([str(i) for i in self.contents])})"


class Variant[T: DBusType](DBusContainerType):
    dbus_code = "v"
    align = 1
    type: T
    signature: str

    def __init__(self, type: T | None = None):

        if type:
            self.type = type
            self.signature = type.to_dbus_str()

    def set_type(self, type: T):
        self.type = type
        self.signature = type.to_dbus_str()

    def is_valid(self, val: Any) -> bool:
        return True  # I don't care enough to check tbh

    def pack(self, data: Any) -> bytes:
        if isinstance(data, tuple) and isinstance(data[0], DBusType):
            t, data = data
            self.set_type(t)

        buf = bytes(
            marshall_str(self.signature, 1)
            + self.type.pack(data)
        )

        return buf

    def to_dbus_str(self) -> str:
        return self.dbus_code


class Dictionary(DBusContainerType):
    """
    Equivalent to the DBus type a{__}
    """

    dbus_code = "{"
    end_dbus_code = "}"
    align = 8
    key: DBusBasicType
    value: DBusType

    def __init__(
        self,
        k_type: DBusBasicType,
        v_type: DBusType,
        *,
        pad_arr_length: bool = True,
    ):
        self.key = k_type
        self.value = v_type
        self.pad_arr_length = pad_arr_length
        self.pack_elem = Struct(k_type, v_type).pack

    def is_valid(self, val: dict[Any, Any]) -> bool:
        k, v = list(val.items())[0]
        return len(val) == 1 and self.key.is_valid(k) and self.value.is_valid(v)

    @override
    def pack(self, data: dict[Any, Any]) -> bytes:
        buf = bytearray()

        for k, v in data.items():
            buf = align_buf(buf, 8)
            buf += self.pack_elem((k, v))

        return bytes(
            len(buf).to_bytes(4, "little") + (b"\0\0\0\0" if self.pad_arr_length else b"") + buf
        )

    def to_dbus_str(self) -> str:
        return f"a{{{self.key.dbus_code}{self.value.dbus_code}}}"

    def __repr__(self) -> str:
        return f"<Dictionary{{{self.key}: {self.value}}}"


class UnixFD(DBusBasicType):
    dbus_code = "h"
    align = 4
    _value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


# Keeping these just in case I need them
# I probably won't though
NUMERIC_TYPES: dict[str, type[DBusType]] = {
    "y": Byte,
    "b": Boolean,
    "n": Int16,
    "q": UInt16,
    "i": Int32,
    "u": UInt32,
    "x": Int64,
    "t": UInt64,
    "d": Double,
}
STRING_TYPES = {
    "s": String,
    "o": ObjectPath,
    "g": Signature,
}
CONTAINER_TYPES = {
    "a": Array,
    "(": Struct,
    "{": Dictionary,
}
OTHER_TYPES = {
    "v": Variant,
    "h": UnixFD,
}

TYPES = NUMERIC_TYPES | STRING_TYPES | CONTAINER_TYPES | OTHER_TYPES
