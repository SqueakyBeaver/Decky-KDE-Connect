from enum import Enum
from typing import Any


class Types(Enum):
    INVALID = "\0"
    BYTE = "y"
    BOOLEAN = "b"
    INT16 = "n"
    UINT16 = "q"
    INT32 = "i"
    UINT32 = "u"
    INT64 = "x"
    UINT64 = "t"
    DOUBLE = "d"
    STRING = "s"
    OBJECT_PATH = "o"
    SIGNATURE = "g"
    ARRAY = "a"
    STRUCT = "("
    STRUCT_END = ")"
    VARIANT = "v"
    DICT_ENTRY = "{"
    DICT_ENTRY_END = "}"
    UNIX_FD = "h"


class Marshaller:
    def __init__(self, signature: str, data: list[Any]):
        self.signature = signature
        self.data = data
        self.buf = bytearray()

    def align(self, boundary: int):
        """
        Align the buffer to a given boundary

        :param boundary: The boundary to align to (i.e. 4)
        """
        offset = boundary - len(self.buf) % boundary

        if offset == 0:
            return

        self.buf.extend([0] * offset)

    _types = {
        Types.BYTE: (1,),
        Types.BOOLEAN: (4,),
        Types.INT16: (2,),
        Types.UINT16: (2,),
        Types.INT32: (4,),
        Types.UINT32: (4,),
        Types.INT64: (8,),
        Types.UINT64: (8,),
        Types.DOUBLE: (8,),
        Types.STRING: (4,),
        Types.OBJECT_PATH: (4,),
        Types.SIGNATURE: (1,),
        Types.ARRAY: (4,),
        Types.STRUCT: (8,),
        Types.VARIANT: (1,),
        Types.DICT_ENTRY: (8,),
        Types.UNIX_FD: (4,),
    }
