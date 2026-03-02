from typing import Any

from dbus.signatures import Array, DBusType, SignatureTree, Struct


class Marshaller:
    def __init__(self, signature: str, data: list[Any]):
        self.sig_str = signature
        self.sig_tree = SignatureTree(signature)
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
        self._marshall(self.data, self.sig_tree.children)

    def _marshall(self, data: list[Any], signature: list[DBusType]):
        """
        Marshall the data in the form of the signature given when creating this object

        :raises TypeError: The type of the data did not match the signature
        """
        for val, sig in zip(data, signature):
            if not sig.is_valid(val):
                raise TypeError(
                    f"<{type(val)} ({val})> is not a compatible type for {repr(sig)}"
                )

            # FIXME: Do some recursive bullshit
            if isinstance(sig, Array):
                self.buf.extend(len(val).to_bytes(4))
                self.align(sig.contents.align)

            self.align(sig.align)
            self.buf.append(val)

    def _marshall_arr(self, array_data: list[Any], array_signature: Array):
        pass

    def _marshall_struct(self, struct_data: tuple[Any], struct_signature: Struct):
        pass
