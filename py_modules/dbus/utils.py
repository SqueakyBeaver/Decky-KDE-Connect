def align_buf[T: bytearray | bytes](buf: T, n: int):
    """
    Align buf to a boundary

    :param buf: The buffer to align
    :param n: The boundary to align to
    :returns: Copy of the aligned buffer
    """
    return buf + b"\0" * (n - len(buf) % n)

def marshall_str(s: str, align: int) -> bytes:
    """
    Marshall a string
    
    :param s: The string to marshall
    :param align: The alignment of the string
    """
    str_len = len(s).to_bytes(align)
    return str_len + s.encode() + b"\0"
