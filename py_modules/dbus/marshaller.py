from abc import ABC, abstractmethod
from struct import Struct
from typing import Any, Iterable, override


class Packer(ABC):
    @abstractmethod
    def pack(self, data: Any, *args, **kwargs) -> bytes:
        pass


class ContainerPacker(Packer):
    @abstractmethod
    def __init__(self, signature: str):
        pass


class StringPacker(Packer):
    def __init__(self, size: int):
        self.size = size

    def pack(self, data: str) -> bytes:
        str_len = len(data).to_bytes(self.size)
        return str_len + data.encode() + b"\0"


class ArrayPacker(ContainerPacker):
    def __init__(self, signature: str):
        """
        Create an array packer

        :param signature: A signature starting with an array token ("a")
            For example, if the signature is xaiy, pass "aiy"
            If the signature is ta(ii)xt, pass "a(ii)xt"
        """
        token = signature[1]
        if token in CONTAINER_TYPES:
            # TODO: Allow python dict to be packed into array of dict entries
            self.content_packer = CONTAINER_TYPES[token][1](signature[1:])

        self.content_align = TYPES[token][0]

    @override
    def pack(self, data: list[Any]) -> bytes:
        return (
            len(data).to_bytes(4)
            + (int(0).to_bytes(self.content_align - (4 % self.content_align)))
            + self.content_packer.pack(data)
        )


class StructPacker(ContainerPacker):
    def __init__(self, signature: str):
        """
        Create a struct packer

        :param signature: A signature starting with a struct token ("(") and containing a ")"
            For example, if the signature is yy(ix)yy, pass "(ix)yy"
        """
        contents_end = signature.rfind(")")
        contents_sig = signature[1:contents_end]

        self.content_packers: list[Struct | Packer] = []
        for idx, i in enumerate(contents_sig):
            if i in BASIC_TYPES:
                self.content_packers.append(BASIC_TYPES[i][1])
            if i in CONTAINER_TYPES:
                self.content_packers.append(CONTAINER_TYPES[i][1](contents_sig[idx:]))

    def pack(self, data: Iterable[Any]) -> bytes:
        content_bytes = bytearray()

        for d, packer in zip(data, self.content_packers):
            if isinstance(packer, StructPacker):
                # Align to 8 bytes. Since we can assume the first struct that is packed
                # always starts on an 8 byte alignment,
                # nested structs should be aligned to 8 bytes
                content_bytes += int(0).to_bytes(8 - (len(content_bytes) % 8))

            content_bytes += packer.pack(d)

        return bytes(content_bytes)


class DictEntryPacker(StructPacker):
    pass


BASIC_TYPES: dict[str, tuple[int, Struct | StringPacker]] = {
    """
    Dict in the form of {token: (alignment, packer)}
    """
    # Numeric Types
    "y": (1, Struct(">B")),
    "b": (4, Struct(">I")),
    "n": (2, Struct(">h")),
    "q": (2, Struct(">H")),
    "i": (4, Struct(">i")),
    "u": (4, Struct(">I")),
    "x": (8, Struct(">q")),
    "t": (8, Struct(">Q")),
    "d": (8, Struct(">d")),
    # String Types
    "s": (4, StringPacker(4)),
    "o": (4, StringPacker(4)),
    "g": (1, StringPacker(1)),
    "h": (4, StringPacker(4)),
}
CONTAINER_TYPES: dict[str, tuple[int, type[ContainerPacker]]] = {
    """
    Dict in the form of {token: (alignment, )}
    """
    "a": (4, ArrayPacker),
    "(": (8, StructPacker),
    "{": (8, DictEntryPacker),
}

TYPES = BASIC_TYPES | CONTAINER_TYPES


class Marshaller:
    def __init__(self, signature: str, data: list[Any]):
        self.sig_str = signature
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

    def marshall(self):
        """
        Marshall the data in the form of the signature given when creating this object

        :raises TypeError: The type of the data did not match the signature
        """

    def _marshall(self, data: list[Any], signature: str):
        """
        Marshall the data in the form of the signature given when creating this object

        :raises TypeError: The type of the data did not match the signature
        """

    def _parse_signature(self, signature: str):
        """
        Parse a given signature string

        :param signature: The signature string to parse
        :returns: todo
        """
        token = signature[0]

        if token in BASIC_TYPES:
            pass
