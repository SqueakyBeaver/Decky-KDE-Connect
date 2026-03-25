from abc import ABC, abstractmethod
from functools import lru_cache
from struct import Struct as CStruct
from typing import Any, Literal, Optional, override

from dbus.utils import align_buf, marshall_str


class DBusType(ABC):
    dbus_code: str
    align: int
    byteorder: Literal["little", "big"]

    def __init__(self, byteorder: Literal["little", "big"] = "little"):
        self.byteorder = byteorder

    @abstractmethod
    def is_valid(self, val: Any) -> bool:
        pass

    @abstractmethod
    def pack(self, data: Any) -> bytes:
        pass

    @abstractmethod
    def decode(self, buf: bytes) -> Any:
        pass

    @abstractmethod
    def to_dbus_str(self) -> str:
        pass


class DBusBasicType(DBusType):
    def __repr__(self) -> str:
        return f"<{type(self).__name__} ({self.dbus_code})>"

    def to_dbus_str(self) -> str:
        return self.dbus_code


class DBusNumericType(DBusBasicType):
    _packer = CStruct("<B")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.byteorder == "big":
            self._packer.format.replace("<", ">")

    def pack(self, data: int):
        return self._packer.pack(data)

    def decode(self, buf: bytes):
        return self._packer.unpack(buf[: self.align])[0]


class DBusStringType(DBusBasicType):
    python_type = str

    def pack(self, data: str):
        return marshall_str(data, self.align, self.byteorder)

    def decode(self, buf: bytes):
        size = buf[0]
        return buf[1 : size + 1].decode()


class DBusContainerType(DBusType):
    pass


class Invalid(DBusBasicType):
    dbus_code = "\0"
    align = 0


class Byte(DBusNumericType):
    dbus_code = "y"
    align = 1
    _packer = CStruct("<B")

    def is_valid(self, val: Any):
        return isinstance(val, int) and val.bit_length() <= 8


class Boolean(DBusNumericType):
    dbus_code = "b"
    align = 4
    _packer = CStruct("<I")

    def is_valid(self, val: Any):
        return isinstance(val, int) and (val == 1 or val == 0)


class Int16(DBusNumericType):
    dbus_code = "n"
    align = 2
    _packer = CStruct("<h")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 16


class UInt16(DBusNumericType):
    dbus_code = "q"
    align = 2
    _packer = CStruct("<H")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 16 and val > 0


class Int32(DBusNumericType):
    dbus_code = "i"
    align = 4
    _packer = CStruct("<i")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 32


class UInt32(DBusNumericType):
    dbus_code = "u"
    align = 4
    _packer = CStruct("<I")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 32 and val > 0


class Int64(DBusNumericType):
    dbus_code = "x"
    align = 8
    _packer = CStruct("<q")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 64


class UInt64(DBusNumericType):
    dbus_code = "t"
    align = 8
    _packer = CStruct("<Q")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 64 and val > 0


class Double(DBusNumericType):
    dbus_code = "d"
    align = 8
    _packer = CStruct("<d")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, float) or isinstance(val, int)

    def pack(self, data: float) -> bytes:
        return self._packer.pack(data)


class String(DBusStringType):
    dbus_code = "s"
    align = 4

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


class ObjectPath(DBusStringType):
    dbus_code = "o"
    align = 4

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


class Signature(DBusStringType):
    dbus_code = "g"
    align = 1

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str) and len(val) < 256


class Array(DBusContainerType, list):
    dbus_code = "a"
    align = 4
    child: DBusType

    def __init__(self, child: DBusType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child = child

    def pack(self, data: list[Any]) -> bytes:
        buf = bytearray()

        for i in data:
            buf += self.child.pack(i)

        return bytes(align_buf(len(buf).to_bytes(4, "little"), self.child.align) + buf)

    def decode(self, buf: bytes):
        size = int.from_bytes(buf[:4], self.byteorder)
        buf = buf[4 + self.child.align:]
        
        ret = []



    def is_valid(self, val):
        return True

    def to_dbus_str(self) -> str:
        return f"a{self.child.to_dbus_str()}"

    def __repr__(self):
        return f"<Array [{self.child}]>"


class Struct(DBusContainerType):
    dbus_code = "("
    align = 8
    children: list[DBusType]

    def __init__(self, *children: DBusType, **kwargs):
        super().__init__(**kwargs)
        self.children = list(children)

    def is_valid(self, val: Any) -> bool:
        # TODO: Check type (I'm lazy)
        return True

    def pack(self, data: tuple[Any, ...]) -> bytes:
        buf = bytearray()

        for child, i in zip(self.children, data):
            buf += child.pack(i)

        return bytes(buf)

    def decode(self, buf: bytes):
        pass

    def to_dbus_str(self) -> str:
        return f"({''.join([c.to_dbus_str() for c in self.children])})"

    def add_child(self, t: DBusType):
        self.children.append(t)

    def __repr__(self):
        return f"<Struct({','.join([str(i) for i in self.children])})"


class Variant(DBusBasicType):
    dbus_code = "v"
    align = 1
    type: DBusType
    signature: str

    def __init__(self, type: DBusType | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if type:
            self.type = type
            self.signature = type.to_dbus_str()

    def set_type(self, type: DBusType):
        self.type = type
        self.signature = type.to_dbus_str()

    def is_valid(self, val: Any) -> bool:
        return True  # I don't care enough to check tbh

    def pack(self, data: Any) -> bytes:
        if isinstance(data, tuple) and isinstance(data[0], DBusType):
            t, data = data
            self.set_type(t)

        buf = bytes(
            marshall_str(self.signature, 1, self.byteorder) + self.type.pack(data)
        )

        return buf

    def decode(self, buf: bytes):
        pass


class Dictionary(DBusContainerType):
    """
    Equivalent to the DBus type a{__}
    """

    align = 8
    key: DBusBasicType
    value: DBusType

    def __init__(
        self,
        k_type: DBusType,
        v_type: DBusType,
        pad_arr_length: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not isinstance(k_type, DBusBasicType):
            raise TypeError(f"Invalid DBus dictionary key type: {k_type}")

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
            len(buf).to_bytes(4, "little")
            + (b"\0\0\0\0" if self.pad_arr_length else b"")
            + buf
        )

    def decode(self, buf: bytes):
        pass

    def to_dbus_str(self) -> str:
        return f"a{{{self.key.to_dbus_str()}{self.value.to_dbus_str()}}}"

    def __repr__(self) -> str:
        return f"<Dictionary{{{self.key}: {self.value}}}"


# TODO: Figure out how/if I should use this
class UnixFD(DBusBasicType):
    dbus_code = "h"
    align = 4

    def pack(self, data: Any) -> bytes:
        return super().pack(data)

    def decode(self, buf: bytes) -> Any:
        return super().decode(buf)

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


NUMERIC_TYPES = {
    "y": Byte,
    "b": Boolean,
    "n": Int16,
    "q": UInt16,
    "i": Int32,
    "u": UInt32,
    "x": Int64,
    "t": UInt64,
    "d": Double,
    "v": Variant,
}
STRING_TYPES = {"s": String, "o": ObjectPath, "g": Signature}
CONTAINER_TYPES = {"a": Array, "(": Struct, "{": Dictionary}
OTHER_TYPES = {"h": UnixFD}
BASIC_TYPES = NUMERIC_TYPES | STRING_TYPES
DBUS_TYPES = NUMERIC_TYPES | STRING_TYPES | CONTAINER_TYPES | OTHER_TYPES


class SignatureParser:
    def __init__(self, sig_str: Optional[str]):
        self.types_list: list[DBusType] = []

        if sig_str:
            self.parse(sig_str)

    @lru_cache
    def parse(self, sig_str: str):
        self.signature = sig_str

        _signature = sig_str
        while _signature:
            (_type, _signature) = self._parse_next(_signature)
            self.types_list.append(_type)

        return self.types_list

    def _parse_next(self, sig_str: str) -> tuple[DBusType, str]:
        """
        Parse a DBus signature string into a list of DBusType objects

        :param sig_str: The signature string to parse
        :param container_stack: The stack of container opening symbols. Used internally
        """
        if not sig_str:
            raise ValueError(
                f"Attempted to parse empty signature (whole signature: {self.signature})"
            )

        tok = sig_str[0]

        if tok not in DBUS_TYPES:
            raise ValueError(f"Invalid token {tok} in signature {self.signature}")

        _signature = sig_str[1:]
        if tok == "a" and sig_str[1] == "{":
            # Skip the "{"
            _signature = _signature[1:]

            (key, _signature) = self._parse_next(_signature)
            (val, _signature) = self._parse_next(_signature)

            if not key or not isinstance(key, DBusBasicType):
                raise ValueError(
                    f"Invalid or missing dictionary key type in signature {self.signature}"
                )
            if not val:
                raise ValueError(
                    f"Missing dictionary value type in signature {self.signature}"
                )

            if _signature[0] != "}":
                raise ValueError(
                    f"Missing closing '}}' or improper dictionary value in signature {self.signature}"
                )

            # Skip the closing "}"
            return (Dictionary(key, val), _signature[1:])
        elif tok == "a":
            (child, _signature) = self._parse_next(_signature)

            return (Array(child), _signature)
        elif tok == "(":
            types: list[DBusType] = []

            while _signature[0] != ")":
                if not _signature:
                    raise ValueError(
                        f"Missing closing ')' in signature {self.signature}"
                    )

                (_type, _signature) = self._parse_next(_signature)
                types.append(_type)

            # Skip the ")"
            return (Struct(*types), _signature[1:])

        return (DBUS_TYPES[tok](), _signature)
