from __future__ import annotations
from py_ecc import bn128
import threading

F = bn128.FQ


def json_method(self: F):
    # Convert the integer to a byte array
    byte_array = self.n.to_bytes(32, "little")

    # Split into four 64-bit integers
    ints = [int.from_bytes(byte_array[i * 8 : i * 8 + 8], "little") for i in range(4)]

    return ints


F.__json__ = json_method


uuid_gen = threading.Lock()
_uuid = 0


def uuid() -> int:
    global _uuid
    with uuid_gen:
        _uuid += 1
        return _uuid


################
# helper types #
################
