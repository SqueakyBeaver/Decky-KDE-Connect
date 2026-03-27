from io import BytesIO
from typing import Literal


def align_buf[T: bytearray | bytes](buf: T, n: int):
    """
    Align buf to a boundary

    :param buf: The buffer to align
    :param n: The boundary to align to
    :returns: Copy of the aligned buffer
    """
    offset = n - len(buf) % n
    if offset == 0 or offset == n:
        return buf

    return buf + b"\0" * offset


def marshall_str(s: str, align: int, byteorder: Literal["little", "big"]) -> bytes:
    """
    Marshall a string

    :param s: The string to marshall
    :param align: The alignment of the string
    """
    str_len = len(s).to_bytes(align, byteorder)
    return str_len + s.encode() + b"\0"


def skip_padding(buf: BytesIO, align: int) -> bytes:
    """
    Skip padding in buf to get to the alignment boundary

    :param buf: The buffer to look at
    :param align: The alignment boundary

    :returns: The bytes that were skipped
    """
    padding = align - (buf.tell() % align)
    if padding == align or padding == 0:
        return b""

    return buf.read(padding)
