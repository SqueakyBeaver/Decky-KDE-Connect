from abc import ABC, abstractmethod
from functools import lru_cache
from struct import Struct as CStruct
from typing import Any, override

# NOTE: This type system will not handle all possible DBus types
# since the most complicated KDE Connect type is a{sv}
# TODO: Implement variants
# TODO: Implement dictionaries


class DBusType(ABC):
    code: str
    align: int

    @abstractmethod
    def is_valid(self, val: Any) -> bool:
        pass

    @abstractmethod
    def marshall(self, data: Any) -> bytes:
        pass



class DBusBasicType(DBusType):
    value: Any = None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} ({self.code})>"


class DBusNumericType(DBusBasicType):
    _packer: CStruct

    def marshall(self, data: int):
        """
        Turn numerical data into a marshalled set of bytes

        :param data: The number to marshall
        """
        return self._packer.pack(data)


class DBusStringType(DBusBasicType):
    def marshall(self, data: str):
        """
        Turn string data into a marshalled set of bytes

        :param data: The string to marshall
        """
        str_len = len(data).to_bytes(self.align)
        return str_len + data.encode() + b"\0"


class DBusContainerType(DBusType):
    pass


class Invalid(DBusBasicType):
    code = "\0"
    align = 0


class Byte(DBusNumericType):
    code = "y"
    align = 1
    value: int
    _packer = CStruct(">B")

    @override
    def is_valid(self, val: Any):
        return isinstance(val, int) and val.bit_length() <= 8


class Boolean(DBusNumericType):
    code = "b"
    align = 4
    value: bool | int
    _packer = CStruct(">I")

    def is_valid(self, val: Any):
        return isinstance(val, int) and (val == 1 or val == 0)


class Int16(DBusNumericType):
    code = "n"
    align = 2
    value: int
    _packer = CStruct(">h")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 16


class UInt16(DBusNumericType):
    code = "q"
    align = 2
    value: int
    _packer = CStruct(">H")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 16 and val > 0


class Int32(DBusNumericType):
    code = "i"
    align = 4
    value: int
    _packer = CStruct(">i")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 32


class UInt32(DBusNumericType):
    code = "u"
    align = 4
    value: int
    _packer = CStruct(">I")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 32 and val > 0


class Int64(DBusNumericType):
    code = "x"
    align = 8
    value: int
    _packer = CStruct(">q")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 64


class UInt64(DBusNumericType):
    code = "t"
    align = 8
    value: int
    _packer = CStruct(">Q")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, int) and val.bit_length() <= 64 and val > 0


class Double(DBusNumericType):
    code = "d"
    align = 8
    value: float
    _packer = CStruct(">d")

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, float) or isinstance(val, int)

    @override
    def marshall(self, data: float) -> bytes:
        """
        Turn a given float into marshalled bytes

        :param data: The float to marshall
        """
        return self._packer.pack(data)


class String(DBusStringType):
    code = "s"
    align = 4
    value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


class ObjectPath(DBusStringType):
    code = "o"
    align = 4
    value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


class Signature(DBusStringType):
    code = "g"
    align = 1
    value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str) and len(val) < 256


class Array[T: DBusType](DBusContainerType, list):
    code = "a"
    align = 4
    size: int
    contents: DBusType
    _type: type

    def __init__(self, arr_type: T):
        self.contents = arr_type
        _type = type(arr_type)

    def __repr__(self):
        return f"<Array[{str(self.contents)}]>"

    def is_valid(self, val: Any) -> bool:
        # TODO: Max array size in bytes is 67108864
        # TODO: Check val type (it's complicated bc of structs and shit and I'm lazy)
        return True

    @override
    def marshall(self, data: list[Any]) -> bytes:
        content_bytes = bytearray()
        for i in data:
            content_bytes += self.contents.marshall(i)

        return len(content_bytes).to_bytes(4) + int(0).to_bytes(
            self.contents.align - (4 % self.contents.align)
        ) + bytes(content_bytes)


class Struct[*T](DBusContainerType):
    code = "("
    end_code = ")"
    align = 8
    size: int
    value: tuple[DBusType, ...]
    _type: tuple[type, ...]

    def __init__(self, *contents: *T):
        self.value = contents # type: ignore
        self._type = tuple([type(i) for i in contents])
        self.child_align = tuple([i.size for i in contents])  # type: ignore

    def __repr__(self):
        return f"<Struct({','.join([str(i) for i in self.value])})"

    def is_valid(self, val: Any) -> bool:
        # TODO: Check type (I'm lazy)
        return True
    
    def marshall(self, data: tuple[Any, ...]) -> bytes:
        content_bytes = bytearray()

        for i, sig in zip(data, self.value):
            content_bytes += sig.marshall(i)
        
        return bytes(content_bytes)


class Variant(DBusBasicType):
    code = "v"
    align = 1

    def is_valid(self, val: Any) -> bool:
        return True  # TODO


class DictEntry(DBusContainerType):
    code = "{"
    end_code = "}"
    align = 8
    key: DBusBasicType
    value: DBusType

    def is_valid(self, val: dict[Any, Any]) -> bool:
        k, v = list(val.items())[0]
        return len(val) == 1 and self.key.is_valid(k) and self.value.is_valid(v)

    @override
    def marshall(self, data: dict[Any, Any]) -> bytes: 
        k, v = list(data.items())[0]
        
        return self.key.marshall(k) + self.value.marshall(v)



class UnixFD(DBusBasicType):
    code = "h"
    align = 4
    value: str

    def is_valid(self, val: Any) -> bool:
        return isinstance(val, str)


CODE_MAPPING: dict[str, type[DBusType]] = {
    "\0": Invalid,
    "y": Byte,
    "b": Boolean,
    "n": Int16,
    "q": UInt16,
    "i": Int32,
    "u": UInt32,
    "x": Int64,
    "t": UInt64,
    "d": Double,
    "s": String,
    "o": ObjectPath,
    "g": Signature,
    "a": Array,
    "(": Struct,
    "v": Variant,
    "{": DictEntry,
    "h": UnixFD,
}


class SignatureTree:
    """
    A Signature represented as a tree
    """

    children: list[DBusType]

    def __init__(self, signature: str):
        self.signature = signature
        self.children = SignatureTree.parse(signature)

    @lru_cache
    @staticmethod
    def parse(signature: str) -> list[DBusType]:
        if not signature:
            return []

        tok_type = CODE_MAPPING[signature[0]]

        if tok_type == Array:
            child, sig = SignatureTree.parse_array(signature[1:])
        elif tok_type == Struct:
            child, sig = SignatureTree.parse_struct((signature[1:]))
        else:
            child = tok_type()
            sig = signature[1:]

        return [child] + SignatureTree.parse(sig)

    @staticmethod
    def parse_array(signature: str) -> tuple[Array[DBusType], str]:
        tok_type = CODE_MAPPING[signature[0]]

        if tok_type == Struct:
            child, sig = SignatureTree.parse_struct(signature[1:])
            return Array(child), sig

        if tok_type == Array:
            child, sig = SignatureTree.parse_array(signature[1:])
            return Array(child), sig

        return Array(tok_type()), signature[1:]

    @staticmethod
    def parse_struct(signature: str) -> tuple[Struct, str]:
        end_idx = signature.rfind(")")
        print(signature, end_idx, signature[end_idx + 1 :])
        struct_type = SignatureTree.parse(signature[:end_idx])

        return Struct(struct_type), signature[end_idx + 1 :]
