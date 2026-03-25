from functools import lru_cache
from typing import Optional

from dbus.signatures import (
    BASIC_TYPES,
    DBUS_TYPES,
    Array,
    DBusBasicType,
    DBusType,
    Dictionary,
    Struct,
)


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

        return (BASIC_TYPES[tok](), _signature)


p = SignatureParser("yyyy")
print(p.types_list)
