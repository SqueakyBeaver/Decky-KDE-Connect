from abc import ABC
from typing import Any


class DBusType(ABC):
    code: str
    size: int


class DBusBasicType(DBusType):
    value: Any = None

    def __repr__(self) -> str:
        if self.value:
            return f"<{type(self).__name__} {self.value}>"
            
        return f"<{type(self).__name__}>"


class DBusContainerType(DBusType):
    pass


class Invalid(DBusBasicType):
    code = "\0"
    size = 0


class Byte(DBusBasicType):
    code = "y"
    size = 1
    value: int


class Boolean(DBusBasicType):
    code = "b"
    size = 4
    value: int


class Int16(DBusBasicType):
    code = "n"
    size = 2
    value: int


class UInt16(DBusBasicType):
    code = "q"
    size = 2
    value: int


class Int32(DBusBasicType):
    code = "i"
    size = 4
    value: int


class UInt32(DBusBasicType):
    code = "u"
    size = 4
    value: int


class Int64(DBusBasicType):
    code = "x"
    size = 8
    value: int


class UInt64(DBusBasicType):
    code = "t"
    size = 8
    value: int


class Double(DBusBasicType):
    code = "d"
    size = 8
    value: float


class String(DBusBasicType):
    code = "s"
    size = 4
    value: str


class ObjectPath(DBusBasicType):
    code = "o"
    size = 4
    value: str


class Signature(DBusBasicType):
    code = "g"
    size = 1
    value: str


class Array[T: DBusType](DBusContainerType, list):
    code = "a"
    size = 4
    value: list[T]
    _type: type

    def __init__(self, arr_type: T):
        self.value = [arr_type]
        _type = type(arr_type)

    def __repr__(self):
        return f"<Array[{str(self.value[0])}]>"


class Struct[*T](DBusContainerType):
    code = "("
    end_code = ")"
    size = 8
    value: tuple[*T]
    _type: tuple[type, ...]

    def __init__(self, *contents: *T):
        self.value = contents
        self._type = tuple([type(i) for i in contents])

    def __repr__(self):
        return f"<Struct({','.join([str(i) for i in self.value])})"


class Variant(DBusBasicType):
    code = "v"
    size = 1


class DictEntry(DBusContainerType):
    code = "{"
    end_code = "}"
    size = 8


class UnixFD(DBusBasicType):
    code = "h"
    size = 4
    value: str


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

    @staticmethod
    def parse(signature: str) -> list[DBusType | None]:
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
        print(signature, end_idx, signature[end_idx + 1:])
        struct_type = SignatureTree.parse(signature[:end_idx])

        return Struct(struct_type), signature[end_idx + 1:]


