import clr
from Osz2Cryptors import XTea

clr.AddReference("Osz2Cryptors")


class XTeaWrapper:
    __slots__ = ("key", "instance")

    def __init__(self, key: bytes) -> None:
        self.key = key
        self.instance = XTea(key)

    def decrypt(self, buf: bytes, start: int, count: int) -> bytes:
        return bytes(self.instance.Decrypt(buf, start, count))
