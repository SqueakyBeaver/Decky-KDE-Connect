from abc import ABC


class DBusType(ABC):
    code: str
    size: int


class DBusBasicType(DBusType):
    pass


class DBusContainerType(DBusType):
    children: list[DBusType]


class invalid(DBusType):
    code = "\0"
    size = 0


class byte(DBusType):
    code = "y"
    size = 1


class boolean(DBusType):
    code = "b"
    size = 4


class int16(DBusType):
    code = "n"
    size = 2


class uint16(DBusType):
    code = "q"
    size = 2


class int32(DBusType):
    code = "i"
    size = 4


class uint32(DBusType):
    code = "u"
    size = 4


class int64(DBusType):
    code = "x"
    size = 8


class uint64(DBusType):
    code = "t"
    size = 8


class double(DBusType):
    code = "d"
    size = 8


class string(DBusType):
    code = "s"
    size = 4


class object_path(DBusType):
    code = "o"
    size = 4


class signature(DBusType):
    code = "g"
    size = 1


class array(DBusContainerType):
    code = "a"
    size = 4


class struct(DBusContainerType):
    code = "("
    end_code = ")"
    size = 8


class variant(DBusType):
    code = "v"
    size = 1


class dict_entry(DBusContainerType):
    code = "{"
    end_code = "}"
    size = 8


class unix_fd(DBusType):
    code = "h"
    size = 4
